"""Modelos del enriquecimiento del perfil de riesgo (HU10)."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.perfilamiento.dominio.modelos import SenalesPerfilamiento


class TipoFuente(str, Enum):
    OPEN_FINANCE = "OPEN_FINANCE"
    OPEN_DATA = "OPEN_DATA"


class OrigenDato(str, Enum):
    FUENTE_EXTERNA = "FUENTE_EXTERNA"
    CACHE = "CACHE"


class Consentimiento(BaseModel):
    consentimiento_id: str = Field(min_length=1)
    cliente_id: str = Field(min_length=1)
    vence_en: datetime


class TrazaFuente(BaseModel):
    """De dónde salió cada dato usado: fuente, proveedor, origen y momento."""

    tipo: TipoFuente
    proveedor: str
    origen: OrigenDato
    obtenido_en: datetime
    latencia_ms: float | None = Field(
        default=None, description="Tiempo de la consulta externa. Nulo si el dato salió de caché."
    )
    motivo_cache: str | None = Field(
        default=None, description="Por qué se usó el dato en caché en lugar de la fuente."
    )


class ResultadoEnriquecimiento(BaseModel):
    cotizacion_id: str
    senales: SenalesPerfilamiento
    fuentes: list[TrazaFuente]
    fecha: datetime
