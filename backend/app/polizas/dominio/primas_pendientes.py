"""Primas pendientes de pago del cliente (HU21).

Una prima pendiente es dinero que el cliente aún debe pagar, o un paso que le falta para que
su póliza exista:

- `RENOVACION`: una renovación iniciada y sin pagar (con número de póliza).
- `COTIZACION`: una cotización vigente sin pagar. Todavía no hay póliza, por eso se muestra el
  ramo y el número de cotización.
- `FIRMA_PENDIENTE`: una cotización ya pagada cuyo contrato falta firmar; la póliza se emite
  al firmar. No hay nada que pagar: solo se avisa.
"""

from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.polizas.dominio.modelos import ZONA_COLOMBIA


class TipoPrimaPendiente(str, Enum):
    RENOVACION = "RENOVACION"
    COTIZACION = "COTIZACION"
    FIRMA_PENDIENTE = "FIRMA_PENDIENTE"


class AccionPrima(str, Enum):
    """Lo que el cliente puede hacer con el ítem."""

    PAGAR = "PAGAR"
    FIRMAR = "FIRMAR"


MENSAJE_FIRMA_PENDIENTE = "Firma tu contrato en el portal web para emitir tu póliza."


class PrimaPendiente(BaseModel):
    model_config = ConfigDict(frozen=True)

    tipo: TipoPrimaPendiente
    accion: AccionPrima
    # Identifica el ítem: la renovación o la cotización.
    referencia_id: str
    # La cotización que se paga con `POST /api/v1/pagos` (o cuyo contrato falta firmar).
    cotizacion_id: str
    poliza_id: str | None = None
    numero_poliza: str | None = None
    ramo: str
    nombre_ramo: str
    monto: Decimal = Field(gt=0)
    moneda: str
    # Sin fecha límite cuando no hay nada que pagar (firma pendiente).
    fecha_limite: AwareDatetime | None = None
    mensaje: str | None = None


class PrimasPendientes(BaseModel):
    model_config = ConfigDict(frozen=True)

    primas: tuple[PrimaPendiente, ...]
    total: int


def fin_de_vigencia(fecha_fin: date) -> datetime:
    """El último instante de la póliza: las 23:59:59 de su último día (Bogotá)."""
    return datetime.combine(fecha_fin, time(23, 59, 59), tzinfo=ZONA_COLOMBIA)


def ordenar_por_fecha_limite(primas: list[PrimaPendiente]) -> list[PrimaPendiente]:
    """Las más urgentes primero; las que no tienen fecha límite al final."""
    return sorted(
        primas,
        key=lambda p: (p.fecha_limite is None, p.fecha_limite.timestamp() if p.fecha_limite else 0),
    )
