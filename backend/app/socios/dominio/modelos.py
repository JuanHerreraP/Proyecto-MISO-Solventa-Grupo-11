"""Modelo de datos de socios de distribución (HU24 / BPM-141)."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.socios.dominio.catalogo import CodigoEndpoint


class EstadoSocio(str, Enum):
    """Estado del socio dentro del proceso de aprovisionamiento."""

    PENDIENTE = "PENDIENTE"
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"


class TipoSeguro(str, Enum):
    """Tipos de seguro que Solventa puede autorizar a un socio."""

    VIAJE = "VIAJE"
    PROTECCION_DISPOSITIVOS = "PROTECCION_DISPOSITIVOS"
    MICROSEGURO_VIDA = "MICROSEGURO_VIDA"
    PARAMETRICO = "PARAMETRICO"
    PROTECCION_PAGOS = "PROTECCION_PAGOS"


class ContactoTecnico(BaseModel):
    """Persona encargada de la integración técnica del socio."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nombre: str = Field(min_length=2, max_length=120)
    correo: str = Field(
        min_length=5,
        max_length=254,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    )
    telefono: str | None = Field(
        default=None,
        min_length=7,
        max_length=20,
        pattern=r"^\+?[0-9][0-9 ()-]{5,18}[0-9]$",
    )


class DatosSocio(BaseModel):
    """Datos suministrados para configurar un socio de distribución."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nit: str = Field(
        min_length=5,
        max_length=20,
        pattern=r"^[0-9]+(?:-[0-9])?$",
        description="NIT sin separadores de miles y con dígito de verificación opcional.",
    )
    razon_social: str = Field(min_length=2, max_length=160)
    contactos_tecnicos: list[ContactoTecnico] = Field(min_length=1)
    pais_operacion: str = Field(
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
        description="Código de país ISO 3166-1 alfa-2.",
    )
    tipos_seguros_autorizados: list[TipoSeguro] = Field(min_length=1)
    endpoints_autorizados: set[CodigoEndpoint] = Field(min_length=1)

    @field_validator("contactos_tecnicos")
    @classmethod
    def contactos_sin_correos_repetidos(
        cls, contactos: list[ContactoTecnico]
    ) -> list[ContactoTecnico]:
        correos = [contacto.correo.lower() for contacto in contactos]
        if len(correos) != len(set(correos)):
            raise ValueError("Los contactos técnicos no pueden repetir el correo.")
        return contactos

    @field_validator("tipos_seguros_autorizados")
    @classmethod
    def tipos_de_seguro_sin_repetidos(cls, tipos: list[TipoSeguro]) -> list[TipoSeguro]:
        if len(tipos) != len(set(tipos)):
            raise ValueError("Los tipos de seguro autorizados no pueden repetirse.")
        return tipos


class SolicitudAltaSocio(DatosSocio):
    """Datos que recibe la API para dar de alta un socio."""


class SolicitudActualizacionSocio(BaseModel):
    """Campos modificables de la configuración de un socio."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    razon_social: str | None = Field(default=None, min_length=2, max_length=160)
    contactos_tecnicos: list[ContactoTecnico] | None = Field(default=None, min_length=1)
    pais_operacion: str | None = Field(
        default=None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"
    )
    tipos_seguros_autorizados: list[TipoSeguro] | None = Field(default=None, min_length=1)
    endpoints_autorizados: set[CodigoEndpoint] | None = Field(default=None, min_length=1)
    estado: EstadoSocio | None = None

    @field_validator("contactos_tecnicos")
    @classmethod
    def contactos_sin_correos_repetidos(
        cls, contactos: list[ContactoTecnico] | None
    ) -> list[ContactoTecnico] | None:
        if contactos is None:
            return None
        correos = [contacto.correo.lower() for contacto in contactos]
        if len(correos) != len(set(correos)):
            raise ValueError("Los contactos técnicos no pueden repetir el correo.")
        return contactos

    @field_validator("tipos_seguros_autorizados")
    @classmethod
    def tipos_de_seguro_sin_repetidos(
        cls, tipos: list[TipoSeguro] | None
    ) -> list[TipoSeguro] | None:
        if tipos is not None and len(tipos) != len(set(tipos)):
            raise ValueError("Los tipos de seguro autorizados no pueden repetirse.")
        return tipos

    @model_validator(mode="after")
    def requiere_al_menos_un_cambio(self) -> "SolicitudActualizacionSocio":
        if not self.model_fields_set:
            raise ValueError("Debe indicar al menos un campo para modificar.")
        if any(getattr(self, campo) is None for campo in self.model_fields_set):
            raise ValueError("Los campos modificados no pueden ser nulos.")
        return self


class SocioDistribucion(DatosSocio):
    """Ficha técnica aprovisionada de un socio de distribución."""

    socio_id: str = Field(min_length=1, max_length=50)
    tenant_id: str = Field(min_length=1, max_length=50)
    estado: EstadoSocio = EstadoSocio.PENDIENTE
    creado_en: datetime
    actualizado_en: datetime
