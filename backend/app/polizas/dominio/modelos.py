"""Modelo de la póliza emitida y su estado efectivo (HU07 / BPM-31).

La póliza guarda una foto del titular y de la cobertura al momento de la emisión (HU12):
el certificado debe mostrar lo que se contrató, aunque luego cambien los datos del cliente.
"""

from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

# Colombia no tiene horario de verano; un desfase fijo evita depender de tzdata en Windows.
ZONA_COLOMBIA = timezone(timedelta(hours=-5), name="America/Bogota")


class RamoPoliza(str, Enum):
    """Mismos ramos que ofrece la cotización (HU03)."""

    VIAJE = "VIAJE"
    PROTECCION_DISPOSITIVOS = "PROTECCION_DISPOSITIVOS"
    VIDA = "VIDA"
    PARAMETRICO = "PARAMETRICO"


NOMBRES_RAMO: dict[RamoPoliza, str] = {
    RamoPoliza.VIAJE: "Seguro de viaje",
    RamoPoliza.PROTECCION_DISPOSITIVOS: "Protección de dispositivos",
    RamoPoliza.VIDA: "Seguro de vida",
    RamoPoliza.PARAMETRICO: "Seguro paramétrico",
}


class EstadoRegistroPoliza(str, Enum):
    """Estado que se persiste. El vencimiento se deriva de las fechas."""

    VIGENTE = "VIGENTE"
    CANCELADA = "CANCELADA"


class EstadoPoliza(str, Enum):
    """Estado que ve el cliente en la billetera."""

    VIGENTE = "VIGENTE"
    VENCIDA = "VENCIDA"
    CANCELADA = "CANCELADA"


class CoberturaPoliza(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=2, max_length=120)
    suma_asegurada: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    descripcion: str | None = Field(default=None, max_length=500)


class Poliza(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    poliza_id: str = Field(min_length=1, max_length=50)
    numero_poliza: str = Field(min_length=3, max_length=40)
    cliente_id: str = Field(min_length=1, max_length=50)
    cotizacion_id: str | None = Field(default=None, max_length=50)
    ramo: RamoPoliza
    estado: EstadoRegistroPoliza = EstadoRegistroPoliza.VIGENTE
    titular_nombre: str = Field(min_length=2, max_length=200)
    titular_tipo_documento: str = Field(min_length=2, max_length=20)
    titular_numero_documento: str = Field(min_length=3, max_length=50)
    fecha_inicio: date
    fecha_fin: date
    prima_total: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    moneda: str = Field(default="COP", pattern=r"^[A-Z]{3}$")
    cobertura_principal: CoberturaPoliza
    codigo_verificacion: str = Field(min_length=8, max_length=64)
    emitida_en: AwareDatetime
    cancelada_en: AwareDatetime | None = None

    @model_validator(mode="after")
    def validar_vigencia(self) -> "Poliza":
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("La fecha de fin no puede ser anterior a la de inicio.")
        if (self.estado is EstadoRegistroPoliza.CANCELADA) != (self.cancelada_en is not None):
            raise ValueError("Una póliza cancelada debe registrar su fecha de cancelación.")
        return self

    def estado_en(self, hoy: date) -> EstadoPoliza:
        if self.estado is EstadoRegistroPoliza.CANCELADA:
            return EstadoPoliza.CANCELADA
        if hoy > self.fecha_fin:
            return EstadoPoliza.VENCIDA
        return EstadoPoliza.VIGENTE

    @property
    def nombre_ramo(self) -> str:
        return NOMBRES_RAMO[self.ramo]

    @property
    def contenido_qr(self) -> str:
        """Lo que codifica el QR del certificado: número y código para verificarlo."""
        return f"SOLVENTA|{self.numero_poliza}|{self.codigo_verificacion}"

    @property
    def documento_enmascarado(self) -> str:
        visibles = self.titular_numero_documento[-4:]
        return f"{self.titular_tipo_documento} ****{visibles}"


class EnlaceCertificado(BaseModel):
    """Enlace temporal para compartir un certificado. Se guarda la huella, no el token."""

    model_config = ConfigDict(extra="forbid")

    huella_token: str = Field(min_length=64, max_length=64)
    poliza_id: str
    cliente_id: str
    creado_en: AwareDatetime
    expira_en: AwareDatetime

    def vigente_en(self, ahora: datetime) -> bool:
        return ahora < self.expira_en


def hoy_en_colombia(ahora: datetime) -> date:
    if ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=UTC)
    return ahora.astimezone(ZONA_COLOMBIA).date()
