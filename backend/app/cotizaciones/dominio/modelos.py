"""Modelo, estados y vigencia de una cotización de seguro (HU03 / BPM-151)."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class RamoSeguro(str, Enum):
    """Ramos disponibles para solicitar una cotización."""

    VIAJE = "VIAJE"
    PROTECCION_DISPOSITIVOS = "PROTECCION_DISPOSITIVOS"
    VIDA = "VIDA"
    PARAMETRICO = "PARAMETRICO"


class EstadoCotizacion(str, Enum):
    """Estados del ciclo de vida de una cotización."""

    BORRADOR = "BORRADOR"
    VIGENTE = "VIGENTE"
    ACEPTADA = "ACEPTADA"
    EXPIRADA = "EXPIRADA"
    CANCELADA = "CANCELADA"


class CoberturaPrincipal(BaseModel):
    """Cobertura principal ofrecida como resultado de la cotización."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=2, max_length=120)
    suma_asegurada: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    descripcion: str | None = Field(default=None, max_length=500)


class Cotizacion(BaseModel):
    """Cotización que conserva los datos del riesgo y su resultado comercial."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    cotizacion_id: str = Field(min_length=1, max_length=50)
    cliente_id: str = Field(min_length=1, max_length=50)
    ramo: RamoSeguro
    datos_riesgo: dict[str, object] = Field(default_factory=dict)
    estado: EstadoCotizacion = EstadoCotizacion.BORRADOR
    prima_total: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=18,
        decimal_places=2,
    )
    moneda: str = Field(default="COP", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    cobertura_principal: CoberturaPrincipal | None = None
    perfil_riesgo_id: str | None = Field(default=None, min_length=1, max_length=50)
    creada_en: AwareDatetime
    vigente_hasta: AwareDatetime | None = None

    @model_validator(mode="after")
    def validar_resultado_y_vigencia(self) -> "Cotizacion":
        if self.vigente_hasta is not None and self.vigente_hasta <= self.creada_en:
            raise ValueError("La vigencia debe terminar después de la creación.")

        if self.estado is not EstadoCotizacion.BORRADOR:
            campos_requeridos = (
                self.prima_total,
                self.cobertura_principal,
                self.vigente_hasta,
            )
            if any(campo is None for campo in campos_requeridos):
                raise ValueError(
                    "Una cotización procesada requiere prima, cobertura y fecha de vigencia."
                )

        return self

    def esta_vigente(self, en: datetime | None = None) -> bool:
        """Indica si la cotización puede aceptarse en un instante determinado."""

        instante = en or datetime.now(UTC)
        if instante.tzinfo is None:
            raise ValueError("El instante consultado debe incluir zona horaria.")

        return (
            self.estado is EstadoCotizacion.VIGENTE
            and self.vigente_hasta is not None
            and self.creada_en <= instante < self.vigente_hasta
        )

    def estado_en(self, en: datetime | None = None) -> EstadoCotizacion:
        """Proyecta EXPIRADA al vencer, sin modificar el registro persistido."""

        instante = en or datetime.now(UTC)
        if instante.tzinfo is None:
            raise ValueError("El instante consultado debe incluir zona horaria.")
        if (
            self.estado is EstadoCotizacion.VIGENTE
            and self.vigente_hasta is not None
            and instante >= self.vigente_hasta
        ):
            return EstadoCotizacion.EXPIRADA
        return self.estado
