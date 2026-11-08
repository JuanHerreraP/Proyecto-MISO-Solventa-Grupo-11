"""Casos de uso de la cancelación de la póliza (HU22 / BPM-35).

- El cliente cancela solo sus pólizas. Una póliza ajena se trata como inexistente (EC08).
- El asesor de ventas cancela las pólizas de sus ventas asistidas (las de las cotizaciones que
  él originó); las de otro asesor se le deniegan.
- Consultar calcula las condiciones y el saldo sin guardar nada. Confirmar los recalcula en el
  servidor y, en una sola transacción, cancela la póliza y registra la cancelación.
- Confirmar exige la confirmación explícita del cliente y es idempotente con la clave
  `Idempotency-Key`: repetir la misma solicitud devuelve la misma cancelación.
- Si la cancelación no se puede procesar, la póliza queda exactamente como estaba.
- Cada cancelación registra quién la pidió y desde qué IP (EC10).
"""

import hashlib
import hmac
import json
import logging
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from typing import Protocol

from app.cotizaciones.repositorio import RepositorioCotizaciones
from app.desembolsos.modelos import Desembolso, EstadoDesembolso
from app.polizas.acceso import poliza_del_solicitante
from app.polizas.dominio.cancelacion import (
    Bloqueo,
    Cancelacion,
    CancelacionNoPermitida,
    CodigoBloqueo,
    ConfirmacionRequerida,
    EstadoDevolucion,
    PeriodoPagado,
    PropuestaCancelacion,
    SolicitudCancelacion,
    cancelacion_id_de,
    periodo_de,
    proponer_cancelacion,
)
from app.polizas.dominio.modelos import EstadoRegistroPoliza, Poliza, hoy_en_colombia
from app.polizas.dominio.renovacion import EstadoRenovacion
from app.polizas.endosos import ClaveIdempotenciaReutilizada, Solicitante
from app.polizas.repositorio import RepositorioPolizas
from app.polizas.repositorio_cancelaciones import (
    CancelacionConcurrente,
    RepositorioCancelaciones,
)
from app.polizas.repositorio_renovaciones import RepositorioRenovaciones
from app.siniestros.modelos import EstadoSiniestro
from app.siniestros.repositorio import RepositorioSiniestros

logger = logging.getLogger(__name__)

_ESTADOS_EN_TRAMITE = frozenset({EstadoSiniestro.REGISTRADO, EstadoSiniestro.EN_EVALUACION})


class ConsultaDesembolsos(Protocol):
    def obtener_por_siniestro(self, siniestro_id: str) -> Desembolso | None: ...


def huella_de_solicitud(poliza_id: str, solicitud: SolicitudCancelacion) -> str:
    """Identifica la solicitud sin la confirmación: lo que importa es el motivo elegido."""
    canonica = json.dumps(
        {"poliza_id": poliza_id, "motivo": solicitud.motivo.value, "detalle": solicitud.detalle},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonica.encode("utf-8")).hexdigest()


def _recortar(valor: str | None, largo: int) -> str | None:
    return valor[:largo] if valor else None


class ServicioCancelaciones:
    def __init__(
        self,
        polizas: RepositorioPolizas,
        cancelaciones: RepositorioCancelaciones,
        siniestros: RepositorioSiniestros,
        desembolsos: ConsultaDesembolsos,
        cotizaciones: RepositorioCotizaciones,
        renovaciones: RepositorioRenovaciones | None = None,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self._polizas = polizas
        self._cancelaciones = cancelaciones
        self._siniestros = siniestros
        self._desembolsos = desembolsos
        self._cotizaciones = cotizaciones
        self._renovaciones = renovaciones
        self._reloj = reloj

    # --- Consulta -----------------------------------------------------------------------

    def _poliza_del_solicitante(self, solicitante: Solicitante, poliza_id: str) -> Poliza:
        return poliza_del_solicitante(self._polizas, self._cotizaciones, solicitante, poliza_id)

    def _siniestros_en_tramite(self, poliza_id: str) -> list[str]:
        """Siniestros abiertos de la póliza.

        Están en trámite los registrados o en evaluación, y los aprobados cuya indemnización
        todavía no se desembolsó por completo.
        """
        abiertos: list[str] = []
        for siniestro in self._siniestros.listar_por_poliza(poliza_id):
            if siniestro.estado in _ESTADOS_EN_TRAMITE:
                abiertos.append(siniestro.siniestro_id)
            elif siniestro.estado is EstadoSiniestro.APROBADO:
                desembolso = self._desembolsos.obtener_por_siniestro(siniestro.siniestro_id)
                if desembolso is None or desembolso.estado is not EstadoDesembolso.COMPLETADA:
                    abiertos.append(siniestro.siniestro_id)
        return abiertos

    def _periodos_pagados(self, poliza: Poliza, hoy: date) -> list[PeriodoPagado]:
        """Periodos con prima pagada: el de la póliza y, si se renovó con anticipación, el actual.

        Una póliza renovada antes de vencer ya muestra el nuevo periodo, que aún no empieza;
        el periodo que sigue en curso es el que registró la renovación.
        """
        periodos = [periodo_de(poliza)]
        if self._renovaciones is None or poliza.fecha_inicio <= hoy:
            return periodos
        for renovacion in self._renovaciones.por_poliza(poliza.poliza_id):
            if (
                renovacion.estado is EstadoRenovacion.APLICADA
                and renovacion.nuevo_inicio == poliza.fecha_inicio
            ):
                anterior = PeriodoPagado(
                    renovacion.anterior_inicio, renovacion.anterior_fin, renovacion.anterior_prima
                )
                return [anterior, *periodos]
        return periodos

    def _proponer(self, poliza: Poliza, ahora: datetime) -> PropuestaCancelacion:
        hoy = hoy_en_colombia(ahora)
        return proponer_cancelacion(
            poliza,
            hoy,
            self._siniestros_en_tramite(poliza.poliza_id),
            self._periodos_pagados(poliza, hoy),
        )

    def consultar(
        self, solicitante: Solicitante, poliza_id: str
    ) -> tuple[PropuestaCancelacion, Cancelacion | None]:
        """Condiciones para cancelar y, si la póliza ya se canceló, su cancelación."""
        poliza = self._poliza_del_solicitante(solicitante, poliza_id)
        propuesta = self._proponer(poliza, self._reloj())
        return propuesta, self._cancelaciones.por_poliza(poliza.poliza_id)

    # --- Confirmación -------------------------------------------------------------------

    def confirmar(
        self,
        solicitante: Solicitante,
        poliza_id: str,
        solicitud: SolicitudCancelacion,
        clave_idempotencia: str | None = None,
    ) -> tuple[Cancelacion, bool]:
        """Cancela la póliza. Devuelve la cancelación y si se creó en esta llamada."""

        poliza = self._poliza_del_solicitante(solicitante, poliza_id)
        huella = huella_de_solicitud(poliza.poliza_id, solicitud)

        if clave_idempotencia:
            previa = self._cancelaciones.por_clave(poliza.poliza_id, clave_idempotencia)
            if previa is not None:
                if not hmac.compare_digest(previa.huella_solicitud, huella):
                    raise ClaveIdempotenciaReutilizada(clave_idempotencia)
                return previa, False

        if not solicitud.confirmo:
            raise ConfirmacionRequerida()

        ahora = self._reloj()
        propuesta = self._proponer(poliza, ahora)
        if not propuesta.cancelable:
            raise CancelacionNoPermitida(propuesta.bloqueos)

        cancelacion = Cancelacion(
            cancelacion_id=cancelacion_id_de(poliza.poliza_id),
            poliza_id=poliza.poliza_id,
            motivo=solicitud.motivo,
            detalle=solicitud.detalle,
            solicitado_por=solicitante.actor_id,
            rol_solicitante=solicitante.rol.value,
            clave_idempotencia=clave_idempotencia or None,
            huella_solicitud=huella,
            ip_solicitante=_recortar(solicitante.ip, 64),
            user_agent=_recortar(solicitante.user_agent, 300),
            fecha_efecto=propuesta.fecha_efecto,
            dias_totales=propuesta.dias_totales,
            dias_no_transcurridos=propuesta.dias_no_transcurridos,
            prima_total=propuesta.prima_total,
            saldo_estimado=propuesta.saldo_estimado,
            moneda=propuesta.moneda,
            estado_devolucion=(
                EstadoDevolucion.PENDIENTE
                if propuesta.saldo_estimado > 0
                else EstadoDevolucion.SIN_SALDO
            ),
            creado_en=ahora,
        )
        cancelada = poliza.model_copy(
            update={"estado": EstadoRegistroPoliza.CANCELADA, "cancelada_en": ahora}
        )
        try:
            self._cancelaciones.registrar(cancelacion, cancelada)
        except CancelacionConcurrente:
            # Otra solicitud la canceló entre la consulta y el guardado.
            raise CancelacionNoPermitida(_ya_cancelada()) from None
        logger.info(
            "Póliza %s cancelada por %s (%s); saldo estimado %s %s",
            poliza.poliza_id,
            solicitante.actor_id,
            solicitante.rol.value,
            cancelacion.saldo_estimado,
            cancelacion.moneda,
        )
        return cancelacion, True


def _ya_cancelada() -> Sequence[Bloqueo]:
    mensaje = "La póliza ya está cancelada."
    return (Bloqueo(codigo=CodigoBloqueo.POLIZA_NO_VIGENTE, mensaje=mensaje),)
