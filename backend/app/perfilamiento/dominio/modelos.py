"""Contratos del perfilamiento de riesgo (HU11).

`SenalesPerfilamiento` es el contrato de entrada que entrega la HU10 (enriquecimiento con
Open Finance / Open Data). Es independiente del proveedor: ningún campo depende de cómo
responde una fuente concreta (EC14).
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class NivelRiesgoZona(str, Enum):
    BAJO = "BAJO"
    MEDIO = "MEDIO"
    ALTO = "ALTO"


class ClasificacionRiesgo(str, Enum):
    BAJO = "BAJO"
    MEDIO = "MEDIO"
    ALTO = "ALTO"


class Dictamen(str, Enum):
    ACEPTADO = "ACEPTADO"
    AJUSTADO = "AJUSTADO"
    RECHAZADO = "RECHAZADO"


class OrigenSenales(str, Enum):
    FUENTES_EXTERNAS = "FUENTES_EXTERNAS"
    CACHE = "CACHE"


class SenalesOpenFinance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comportamiento_pago: float = Field(
        ge=0, le=1, description="1.0 = historial de pago impecable; 0.0 = incumplimiento total."
    )
    nivel_endeudamiento: float = Field(
        ge=0, le=1, description="Proporción de los ingresos comprometida en deudas."
    )


class SenalesOpenData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estabilidad: float = Field(
        ge=0, le=1, description="Estabilidad sociodemográfica y laboral; 1.0 = muy estable."
    )
    riesgo_zona: NivelRiesgoZona = Field(description="Riesgo de la zona donde está el inmueble.")


class SenalesPerfilamiento(BaseModel):
    """Modelo unificado de señales que produce la HU10 y consume la HU11."""

    model_config = ConfigDict(extra="forbid")

    cliente_id: str = Field(min_length=1)
    consentimiento_id: str = Field(min_length=1)
    consentimiento_vigente: bool
    open_finance: SenalesOpenFinance
    open_data: SenalesOpenData
    origen: OrigenSenales = OrigenSenales.FUENTES_EXTERNAS


class ReglaAplicada(BaseModel):
    """Traza de una regla usada en el cálculo, para explicar la decisión."""

    codigo: str
    descripcion: str
    efecto: str


class PerfilRiesgo(BaseModel):
    """Resultado completo del perfilamiento. Lo consulta el Analista de Riesgos."""

    perfil_id: str
    cliente_id: str
    consentimiento_id: str
    puntaje_riesgo: int = Field(ge=0, le=100, description="0 = riesgo mínimo; 100 = máximo.")
    clasificacion: ClasificacionRiesgo
    dictamen: Dictamen
    factor_riesgo: float | None = Field(
        description="Multiplicador de la prima base para el motor de precios. Nulo si se rechaza."
    )
    extraprima_porcentaje: float = Field(ge=0)
    origen_senales: OrigenSenales
    version_reglas: str
    reglas_aplicadas: list[ReglaAplicada]
    fecha_calculo: datetime
    tiempo_calculo_ms: float


class OfertaCliente(BaseModel):
    """Vista para el Cliente Asegurado: la oferta y su explicación, sin reglas internas."""

    cliente_id: str
    dictamen: Dictamen
    extraprima_porcentaje: float
    explicacion: str
    fecha_calculo: datetime
