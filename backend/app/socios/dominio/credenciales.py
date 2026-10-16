"""Credenciales estándar para integrar un socio con el gateway."""

import secrets
from datetime import datetime

from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, Field

from app.socios.dominio.catalogo import CodigoEndpoint


class CredencialesSocio(BaseModel):
    """Datos que se almacenan para autenticar a un socio."""

    model_config = ConfigDict(extra="forbid")

    socio_id: str = Field(min_length=1, max_length=50)
    tenant_id: str = Field(min_length=1, max_length=50)
    client_id: str = Field(min_length=1, max_length=100)
    secret_hash: str = Field(min_length=1)
    scopes: set[CodigoEndpoint] = Field(min_length=1)
    activo: bool = True
    creado_en: datetime


class CredencialesEmitidas(BaseModel):
    """Credenciales que se entregan una sola vez al aprovisionarlas."""

    model_config = ConfigDict(extra="forbid")

    socio_id: str
    tenant_id: str
    client_id: str
    client_secret: str
    scopes: set[CodigoEndpoint]
    creado_en: datetime


class TokenAccesoSocio(BaseModel):
    """Token temporal entregado a un socio autenticado."""

    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    scope: str


class SocioAutenticado(BaseModel):
    """Identidad técnica extraída de un token válido de socio."""

    model_config = ConfigDict(extra="forbid")

    client_id: str
    socio_id: str
    tenant_id: str
    scopes: set[CodigoEndpoint]


password_hash = PasswordHash.recommended()


def generar_credenciales(
    socio_id: str,
    tenant_id: str,
    scopes: set[CodigoEndpoint],
    creado_en: datetime,
) -> tuple[CredencialesSocio, str]:
    """Genera las credenciales y devuelve el secreto plano una sola vez."""

    client_id = f"solv_{secrets.token_urlsafe(12)}"
    client_secret = f"solv_secret_{secrets.token_urlsafe(32)}"
    credenciales = CredencialesSocio(
        socio_id=socio_id,
        tenant_id=tenant_id,
        client_id=client_id,
        secret_hash=password_hash.hash(client_secret),
        scopes=scopes,
        creado_en=creado_en,
    )
    return credenciales, client_secret


def verificar_secret(
    client_secret: str,
    credenciales: CredencialesSocio,
) -> bool:
    """Verifica un secreto sin exponer ni comparar el hash manualmente."""

    return password_hash.verify(client_secret, credenciales.secret_hash)
