"""Evaluación de siniestros por Operaciones/Siniestros y disparo del desembolso (HU15).

- Solo Operaciones/Siniestros aprueba o rechaza; el cliente nunca puede aprobar su siniestro
  ni ordenar un desembolso.
- Aprobar fija el monto (por defecto la estimación de daños) con tope en la suma asegurada
  de la póliza, deja quién y cuándo, y ordena el desembolso en la misma operación.
- Repetir la misma aprobación es inocuo: devuelve el mismo siniestro y el mismo desembolso.
- Los siniestros paramétricos se aprueban solos por la suma contratada.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from app.desembolsos.modelos import Desembolso
from app.desembolsos.servicio import ServicioDesembolsos
from app.polizas.repositorio import RepositorioPolizas
from app.siniestros.modelos import EstadoSiniestro, Siniestro
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
    ):
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
        siniestro = self._obtener(siniestro_id)
        if siniestro.estado is EstadoSiniestro.APROBADO:
            if monto is not None and monto != siniestro.monto_aprobado:
                raise SiniestroYaEvaluado(siniestro.estado)
            # Repetición de la misma aprobación: se asegura el desembolso y se devuelve.
            return siniestro, self._desembolsos.desembolsar(siniestro)
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
        return aprobado, self._desembolsos.desembolsar(aprobado)

    def aprobar_automatico(self, siniestro: Siniestro) -> Desembolso | None:
        """Aprobación del siniestro paramétrico.

        Un fallo no interrumpe la recepción del evento: el siniestro queda en la bandeja de
        Operaciones, que puede aprobarlo o reintentar el desembolso.
        """
        try:
            _, desembolso = self.aprobar(siniestro.siniestro_id, EVALUADOR_AUTOMATICO)
        except Exception:
            logger.exception(
                "No se pudo aprobar automáticamente el siniestro %s; queda para Operaciones",
                siniestro.siniestro_id,
            )
            return None
        return desembolso

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
        return rechazado

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
