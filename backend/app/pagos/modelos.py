"""Modelo de dominio del pago del recaudo inicial (HU13)."""

import re
from decimal import Decimal
from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class EstadoPago(str, Enum):
    PENDIENTE = "PENDIENTE"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"

    @property
    def es_final(self) -> bool:
        return self is not EstadoPago.PENDIENTE


class MetodoPago(str, Enum):
    TARJETA = "TARJETA"
    PSE = "PSE"


# Un PAN tiene entre 13 y 19 dígitos; si el "token" lo parece, el cliente no tokenizó.
_PARECE_PAN = re.compile(r"^[\d\s-]{13,23}$")


class Pago(BaseModel):
    """Intento de recaudo asociado a una cotización. Nunca guarda datos de tarjeta."""

    model_config = ConfigDict(extra="forbid")

    pago_id: str = Field(min_length=1, max_length=50)
    cotizacion_id: str = Field(min_length=1, max_length=50)
    cliente_id: str = Field(min_length=1, max_length=50)
    idempotency_key: str = Field(min_length=1, max_length=64)
    huella_solicitud: str = Field(min_length=64, max_length=64)
    metodo: MetodoPago
    monto: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    moneda: str = Field(min_length=3, max_length=3)
    estado: EstadoPago = EstadoPago.PENDIENTE
    referencia_pasarela: str | None = Field(default=None, max_length=100)
    url_redireccion: str | None = Field(default=None, max_length=500)
    motivo_rechazo: str | None = Field(default=None, max_length=200)
    creado_en: AwareDatetime
    actualizado_en: AwareDatetime


def validar_token_pago(valor: str | None) -> str | None:
    """Rechaza valores que parezcan un número de tarjeta en claro."""

    if valor is not None and _PARECE_PAN.match(valor):
        raise ValueError("Se recibió un número de tarjeta; debe enviarse el token de la pasarela.")
    return valor


class SolicitudPago(BaseModel):
    """Cuerpo de la solicitud de pago: sólo token (tarjeta) o banco (PSE)."""

    model_config = ConfigDict(extra="forbid")

    cotizacion_id: str = Field(min_length=1, max_length=50)
    metodo: MetodoPago
    token_tarjeta: str | None = Field(default=None, min_length=8, max_length=200)
    codigo_banco: str | None = Field(default=None, min_length=1, max_length=20)
    url_retorno: str | None = Field(default=None, max_length=500)

    _sin_pan = field_validator("token_tarjeta")(validar_token_pago)
