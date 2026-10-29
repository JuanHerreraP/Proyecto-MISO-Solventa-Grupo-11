"""Modelo de dominio del siniestro y el contrato de registro manual (HU20)."""

from datetime import date, time
from decimal import Decimal
from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class EstadoSiniestro(str, Enum):
    """Ciclo de vida del siniestro. En la parte manual solo se usa REGISTRADO."""

    REGISTRADO = "REGISTRADO"
    EN_EVALUACION = "EN_EVALUACION"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"


class OrigenSiniestro(str, Enum):
    """MANUAL para el registro desde el portal; AUTOMATICO queda para la fase paramétrica."""

    MANUAL = "MANUAL"
    AUTOMATICO = "AUTOMATICO"


class Siniestro(BaseModel):
    """Reclamación asociada a una póliza de un cliente.

    Se conserva `cliente_id` además de `poliza_id` para trazabilidad y autorización.
    `registrado_por` puede diferir de `cliente_id` cuando lo registra un asesor.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    siniestro_id: str = Field(min_length=1, max_length=50)
    cliente_id: str = Field(min_length=1, max_length=50)
    poliza_id: str = Field(min_length=1, max_length=50)
    origen: OrigenSiniestro = OrigenSiniestro.MANUAL
    estado: EstadoSiniestro = EstadoSiniestro.REGISTRADO
    # Identificador del evento externo que originó el siniestro (solo origen AUTOMATICO / HU20).
    # Es la clave de idempotencia: un mismo evento_id no debe generar siniestros duplicados.
    evento_id: str | None = Field(default=None, max_length=120)
    fecha_evento: date
    hora_evento: time
    lugar: str = Field(min_length=1, max_length=200)
    descripcion: str = Field(min_length=10, max_length=2000)
    estimacion_danos: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    moneda: str = Field(default="COP", pattern=r"^[A-Z]{3}$")
    registrado_por: str = Field(min_length=1, max_length=50)
    registrado_en: AwareDatetime


class SolicitudSiniestro(BaseModel):
    """Cuerpo del registro manual. El cliente nunca envía su propio identificador."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    poliza_id: str = Field(min_length=1, max_length=50)
    fecha_evento: date
    hora_evento: time
    lugar: str = Field(min_length=1, max_length=200)
    descripcion: str = Field(min_length=10, max_length=2000)
    estimacion_danos: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
