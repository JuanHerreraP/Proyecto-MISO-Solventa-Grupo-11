"""Generación de tokens JWT para integraciones de socios."""

import os
from datetime import datetime, timedelta, timezone

import jwt

from app.identidad.tokens import (
    PRIVATE_KEY_PATH,
    PUBLIC_KEY_PATH,
    TokenExpiradoError,
    TokenInvalidoError,
)
from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.dominio.credenciales import CredencialesSocio

ACCESS_TOKEN_SOCIO_MINUTES = int(os.getenv("SOCIOS_ACCESS_TOKEN_MINUTES", "15"))


def crear_access_token_socio(
    credenciales: CredencialesSocio,
    scopes: set[CodigoEndpoint],
) -> tuple[str, int]:
    """Crea un token corto para el flujo OAuth client credentials."""

    ahora = datetime.now(timezone.utc)
    expiracion = ahora + timedelta(minutes=ACCESS_TOKEN_SOCIO_MINUTES)
    expires_in = ACCESS_TOKEN_SOCIO_MINUTES * 60
    payload = {
        "sub": credenciales.client_id,
        "socio_id": credenciales.socio_id,
        "tenant_id": credenciales.tenant_id,
        "scope": sorted(scope.value for scope in scopes),
        "iat": ahora,
        "exp": expiracion,
        "type": "partner_access",
    }
    token = jwt.encode(
        payload,
        PRIVATE_KEY_PATH.read_text(),
        algorithm="RS256",
    )
    return token, expires_in


def validar_access_token_socio(token: str) -> dict:
    """Valida firma, expiración y claims mínimos de un token de socio."""

    try:
        payload = jwt.decode(
            token,
            PUBLIC_KEY_PATH.read_text(),
            algorithms=["RS256"],
        )
    except jwt.ExpiredSignatureError as error:
        raise TokenExpiradoError("El token del socio ha expirado.") from error
    except jwt.InvalidTokenError as error:
        raise TokenInvalidoError("El token del socio no es válido.") from error

    if payload.get("type") != "partner_access":
        raise TokenInvalidoError("El token no corresponde a una integración de socio.")

    requeridos = ("sub", "socio_id", "tenant_id", "scope")
    if any(not payload.get(claim) for claim in requeridos):
        raise TokenInvalidoError("El token del socio no contiene los claims requeridos.")

    return payload
