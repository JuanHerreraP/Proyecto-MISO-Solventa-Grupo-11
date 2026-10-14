"""Generación de tokens JWT para integraciones de socios."""

import os
from datetime import datetime, timedelta, timezone

import jwt

from app.identidad.tokens import PRIVATE_KEY_PATH
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
