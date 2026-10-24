"""Proceso de firma electrónica y sus reglas de OTP (HU14 / BPM-60)."""

from datetime import datetime, timedelta
from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.firmas.contrato import ContratoSeguro

VIGENCIA_OTP = timedelta(minutes=5)
MAX_INTENTOS_POR_CODIGO = 3
MAX_ENVIOS = 3
ESPERA_ENTRE_ENVIOS = timedelta(seconds=30)


class EstadoFirma(str, Enum):
    PENDIENTE = "PENDIENTE"
    FIRMADA = "FIRMADA"
    BLOQUEADA = "BLOQUEADA"


class CanalOtp(str, Enum):
    SMS = "SMS"
    EMAIL = "EMAIL"


class ProcesoFirma(BaseModel):
    """Un proceso por cotización pagada. Guarda la foto del contrato presentado."""

    model_config = ConfigDict(extra="forbid")

    firma_id: str = Field(min_length=1, max_length=50)
    cotizacion_id: str = Field(min_length=1, max_length=50)
    pago_id: str = Field(min_length=1, max_length=50)
    cliente_id: str = Field(min_length=1, max_length=50)
    estado: EstadoFirma = EstadoFirma.PENDIENTE
    contrato: ContratoSeguro
    huella_documento: str = Field(min_length=64, max_length=64)

    # OTP vigente: solo se guarda su HMAC, nunca el código.
    otp_hash: str | None = Field(default=None, min_length=64, max_length=64)
    otp_canal: CanalOtp | None = None
    otp_destino: str | None = Field(default=None, max_length=255)
    otp_emitido_en: AwareDatetime | None = None
    otp_expira_en: AwareDatetime | None = None
    intentos_fallidos: int = Field(default=0, ge=0)
    envios: int = Field(default=0, ge=0)
    referencia_envio: str | None = Field(default=None, max_length=100)

    # Metadatos de la firma (EC10).
    firmado_en: AwareDatetime | None = None
    firmante_id: str | None = Field(default=None, max_length=50)
    ip_firmante: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=300)
    referencia_proveedor: str | None = Field(default=None, max_length=100)
    sello_proveedor: str | None = Field(default=None, max_length=200)

    creado_en: AwareDatetime
    actualizado_en: AwareDatetime

    def documento_integro(self) -> bool:
        return self.contrato.huella() == self.huella_documento

    @property
    def intentos_restantes(self) -> int:
        if self.otp_hash is None:
            return 0
        return max(MAX_INTENTOS_POR_CODIGO - self.intentos_fallidos, 0)

    @property
    def envios_restantes(self) -> int:
        return max(MAX_ENVIOS - self.envios, 0)

    def reenvio_disponible_en(self) -> datetime | None:
        if self.otp_emitido_en is None:
            return None
        return self.otp_emitido_en + ESPERA_ENTRE_ENVIOS


def enmascarar(destino: str, canal: CanalOtp) -> str:
    """Lo que el cliente ve del destino del código: suficiente para reconocerlo."""
    if canal is CanalOtp.EMAIL:
        usuario, _, dominio = destino.partition("@")
        return f"{usuario[:2]}***@{dominio}"
    digitos = "".join(c for c in destino if c.isdigit())
    return f"*** *** {digitos[-4:]}"
