"""Lo que la API de cancelación expone al cliente (HU22 / BPM-35).

Nunca incluye la huella de la solicitud, la clave de idempotencia, la IP ni el agente de
usuario: son evidencia de auditoría, no datos para el cliente.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.polizas.dominio.cancelacion import (
    Cancelacion,
    EstadoDevolucion,
    MotivoCancelacion,
    PropuestaCancelacion,
)


class CancelacionVista(BaseModel):
    cancelacion_id: str
    poliza_id: str
    motivo: MotivoCancelacion
    detalle: str | None
    fecha_efecto: date
    dias_totales: int
    dias_no_transcurridos: int
    prima_total: Decimal
    saldo_estimado: Decimal
    moneda: str
    estado_devolucion: EstadoDevolucion
    creado_en: datetime


class CondicionesCancelacion(PropuestaCancelacion):
    """Condiciones para cancelar y, si la póliza ya se canceló, el registro de la cancelación."""

    cancelacion: CancelacionVista | None = None


def a_cancelacion(cancelacion: Cancelacion) -> CancelacionVista:
    return CancelacionVista(
        cancelacion_id=cancelacion.cancelacion_id,
        poliza_id=cancelacion.poliza_id,
        motivo=cancelacion.motivo,
        detalle=cancelacion.detalle,
        fecha_efecto=cancelacion.fecha_efecto,
        dias_totales=cancelacion.dias_totales,
        dias_no_transcurridos=cancelacion.dias_no_transcurridos,
        prima_total=cancelacion.prima_total,
        saldo_estimado=cancelacion.saldo_estimado,
        moneda=cancelacion.moneda,
        estado_devolucion=cancelacion.estado_devolucion,
        creado_en=cancelacion.creado_en,
    )


def a_condiciones(
    propuesta: PropuestaCancelacion, cancelacion: Cancelacion | None
) -> CondicionesCancelacion:
    return CondicionesCancelacion(
        **propuesta.model_dump(),
        cancelacion=a_cancelacion(cancelacion) if cancelacion is not None else None,
    )
