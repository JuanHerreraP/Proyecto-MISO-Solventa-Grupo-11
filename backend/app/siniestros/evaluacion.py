"""Evaluación de siniestros por Operaciones/Siniestros y disparo del desembolso (HU15).

- Solo Operaciones/Siniestros aprueba o rechaza; el cliente nunca puede aprobar su siniestro
  ni ordenar un desembolso.
- Aprobar fija el monto (por defecto la estimación de daños) con tope en la suma asegurada
  de la póliza, deja quién y cuándo, y ordena el desembolso en la misma operación.
- Repetir la misma aprobación es inocuo: devuelve el mismo siniestro y el mismo desembolso.
- Los siniestros paramétricos se aprueban solos por la suma contratada. Con un publicador de
  eventos configurado (SNS), la aprobación automática no ordena el pago: publica el evento y el
  consumidor de pagos lo ordena a su ritmo (patrón de mensajería asíncrona).
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from app.desembolsos.modelos import Desembolso
from app.desembolsos.servicio import ServicioDesembolsos
from app.eventos.publicador import PublicadorNegocio
from app.notificaciones.eventos import estado_siniestro, pago_parametrico
from app.notificaciones.servicio import ServicioNotificaciones
from app.polizas.repositorio import RepositorioPolizas
from app.siniestros.eventos import evento_pago_parametrico
from app.siniestros.modelos import EstadoSiniestro, OrigenSiniestro, Siniestro
from app.siniestros.repositorio import RepositorioSiniestros

logger = logging.getLogger(__name__)

EVALUADOR_AUTOMATICO = "SISTEMA"


class SiniestroNoEncontrado(Exception):
    pass


class SiniestroYaEvaluado(Exception):
    """El siniestro ya tiene una decisión distinta de la que se pide."""

    def __init__(self, estado: EstadoSiniestro):
        super().__init__(estado.value)
        self.estado = estado


class MontoInvalido(Exception):
    def __init__(self, tope: Decimal):
        super().__init__(str(tope))
        self.tope = tope


class ServicioEvaluacion:
    def __init__(
        self,
        siniestros: RepositorioSiniestros,
        polizas: RepositorioPolizas,
        desembolsos: ServicioDesembolsos,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        notificaciones: ServicioNotificaciones | None = None,
        publicador: PublicadorNegocio | None = None,
    ):
        self._notificaciones = notificaciones
        self._publicador = publicador
        self._siniestros = siniestros
        self._polizas = polizas
        self._desembolsos = desembolsos
        self._reloj = reloj

    def bandeja(
        self, estado: EstadoSiniestro | None = None
    ) -> list[tuple[Siniestro, Desembolso | None]]:
        return [
            (s, self._desembolsos.obtener_por_siniestro(s.siniestro_id))
            for s in self._siniestros.listar(estado)
        ]

    def aprobar(
        self, siniestro_id: str, evaluador_id: str, monto: Decimal | None = None
    ) -> tuple[Siniestro, Desembolso]:
        aprobado = self._aprobar(siniestro_id, evaluador_id, monto)
        # Repetir la misma aprobación asegura el desembolso y devuelve el mismo.
        return aprobado, self._desembolsos.desembolsar(aprobado)

    def _aprobar(
        self, siniestro_id: str, evaluador_id: str, monto: Decimal | None = None
    ) -> Siniestro:
        """Deja el siniestro aprobado y avisa al cliente, sin ordenar el desembolso."""
        siniestro = self._obtener(siniestro_id)
        if siniestro.estado is EstadoSiniestro.APROBADO:
            if monto is not None and monto != siniestro.monto_aprobado:
                raise SiniestroYaEvaluado(siniestro.estado)
            return siniestro
        if siniestro.estado is EstadoSiniestro.RECHAZADO:
            raise SiniestroYaEvaluado(siniestro.estado)

        tope = self._tope(siniestro)
        monto_final = monto if monto is not None else min(siniestro.estimacion_danos, tope)
        if monto_final <= 0 or monto_final > tope:
            raise MontoInvalido(tope)

        aprobado = siniestro.model_copy(
            update={
                "estado": EstadoSiniestro.APROBADO,
                "monto_aprobado": monto_final.quantize(Decimal("0.01")),
                "evaluado_por": evaluador_id,
                "evaluado_en": self._reloj(),
                "motivo_rechazo": None,
            }
        )
        self._siniestros.guardar(aprobado)
        self._notificar_decision(aprobado)
        return aprobado

    def aprobar_automatico(self, siniestro: Siniestro) -> Desembolso | None:
        """Aprobación del siniestro paramétrico.

        Sin publicador, ordena el desembolso en el mismo proceso. Con publicador, aprueba y
        publica el evento; el pago lo ordena el consumidor y aquí se devuelve None.

        Un fallo no interrumpe la recepción del evento: el siniestro queda en la bandeja de
        Operaciones, que puede aprobarlo o reintentar el desembolso.
        """
        try:
            if self._publicador is None:
                _, desembolso = self.aprobar(siniestro.siniestro_id, EVALUADOR_AUTOMATICO)
                return desembolso
            aprobado = self._aprobar(siniestro.siniestro_id, EVALUADOR_AUTOMATICO)
        except Exception:
            logger.exception(
                "No se pudo aprobar automáticamente el siniestro %s; queda para Operaciones",
                siniestro.siniestro_id,
            )
            return None
        self._publicar_pago(aprobado)
        return None

    def _publicar_pago(self, siniestro: Siniestro) -> None:
        """Publica el evento del pago. Un fallo no deshace la aprobación ya guardada.

        Si SNS no confirma, el siniestro queda aprobado sin desembolso y el barrido de
        pendientes lo vuelve a publicar con el mismo identificador de evento.
        """
        try:
            self._publicador.publicar(evento_pago_parametrico(siniestro))
        except Exception:
            logger.exception(
                "No se pudo publicar el pago del siniestro %s; lo retoma el barrido",
                siniestro.siniestro_id,
            )

    def rechazar(self, siniestro_id: str, evaluador_id: str, motivo: str) -> Siniestro:
        siniestro = self._obtener(siniestro_id)
        if siniestro.estado is EstadoSiniestro.RECHAZADO:
            return siniestro
        if siniestro.estado is EstadoSiniestro.APROBADO:
            raise SiniestroYaEvaluado(siniestro.estado)
        rechazado = siniestro.model_copy(
            update={
                "estado": EstadoSiniestro.RECHAZADO,
                "evaluado_por": evaluador_id,
                "evaluado_en": self._reloj(),
                "motivo_rechazo": motivo,
            }
        )
        self._siniestros.guardar(rechazado)
        self._notificar_decision(rechazado)
        return rechazado

    def _notificar_decision(self, siniestro: Siniestro) -> None:
        """Avisa al cliente la decisión (HU05).

        Un siniestro paramétrico aprobado se avisa como pago (con el monto y la póliza); el resto
        como cambio de estado. Un fallo aquí nunca deshace ni frena la decisión ya tomada: el
        cliente igual verá el estado en la app.
        """
        if self._notificaciones is None:
            return
        try:
            poliza = self._polizas.obtener(siniestro.poliza_id)
            es_pago_parametrico = (
                siniestro.estado is EstadoSiniestro.APROBADO
                and siniestro.origen is OrigenSiniestro.AUTOMATICO
            )
            evento = (pago_parametrico if es_pago_parametrico else estado_siniestro)(
                siniestro, poliza
            )
            self._notificaciones.notificar_evento(siniestro.cliente_id, evento)
        except Exception:
            logger.exception(
                "No se pudo notificar la decisión del siniestro %s", siniestro.siniestro_id
            )

    def reintentar_desembolso(self, siniestro_id: str) -> Desembolso:
        siniestro = self._obtener(siniestro_id)
        if siniestro.estado is not EstadoSiniestro.APROBADO:
            raise SiniestroYaEvaluado(siniestro.estado)
        if self._desembolsos.obtener_por_siniestro(siniestro_id) is None:
            # Aprobado pero la orden no alcanzó a crearse (un fallo tras aprobar): se crea ahora.
            return self._desembolsos.desembolsar(siniestro)
        return self._desembolsos.reintentar(siniestro_id)

    def _obtener(self, siniestro_id: str) -> Siniestro:
        siniestro = self._siniestros.obtener(siniestro_id)
        if siniestro is None:
            raise SiniestroNoEncontrado(siniestro_id)
        return siniestro

    def _tope(self, siniestro: Siniestro) -> Decimal:
        poliza = self._polizas.obtener(siniestro.poliza_id)
        if poliza is None:
            return siniestro.estimacion_danos
        return poliza.cobertura_principal.suma_asegurada
