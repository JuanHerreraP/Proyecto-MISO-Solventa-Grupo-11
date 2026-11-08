"""Lo que la API de renovación expone al cliente (HU22 / BPM-35).

Nunca incluye la clave de idempotencia, la IP ni el agente de usuario: son evidencia de
auditoría, no datos para el cliente.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.polizas.dominio.renovacion import EstadoRenovacion, PropuestaRenovacion, Renovacion


class RenovacionVista(BaseModel):
    """La renovación y lo necesario para pagarla: `cotizacion_id` y `prima_total` (el monto)."""

    renovacion_id: str
    poliza_id: str
    cotizacion_id: str
    estado: EstadoRenovacion
    nuevo_inicio: date
    nuevo_fin: date
    prima_total: Decimal
    moneda: str
    vigente_hasta: datetime
    pago_id: str | None
    aplicada_en: datetime | None
    motivo_no_aplicada: str | None


class CondicionesRenovacion(PropuestaRenovacion):
    """La propuesta y, si hay una renovación en curso esperando el pago, esa renovación."""

    renovacion: RenovacionVista | None = None


def a_renovacion(renovacion: Renovacion, estado: EstadoRenovacion) -> RenovacionVista:
    return RenovacionVista(
        renovacion_id=renovacion.renovacion_id,
        poliza_id=renovacion.poliza_id,
        cotizacion_id=renovacion.cotizacion_id,
        estado=estado,
        nuevo_inicio=renovacion.nuevo_inicio,
        nuevo_fin=renovacion.nuevo_fin,
        prima_total=renovacion.prima_total,
        moneda=renovacion.moneda,
        vigente_hasta=renovacion.vigente_hasta,
        pago_id=renovacion.pago_id,
        aplicada_en=renovacion.aplicada_en,
        motivo_no_aplicada=renovacion.motivo_no_aplicada,
    )


def a_condiciones(
    propuesta: PropuestaRenovacion, renovacion: RenovacionVista | None
) -> CondicionesRenovacion:
    return CondicionesRenovacion(**propuesta.model_dump(), renovacion=renovacion)
