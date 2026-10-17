"""Tokens firmados para autenticar a Solventa ante proveedores externos."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt

DURACION_TOKEN_SEGUNDOS = 60


def crear_token_proveedor(
    *,
    llave_privada: str,
    emisor: str,
    audiencia: str,
    servicio: str = "servicio-perfilamiento",
    ahora: datetime | None = None,
) -> str:
    """Genera un JWT RS256 corto para una transmisión hacia un proveedor."""

    if not all((llave_privada, emisor, audiencia, servicio)):
        raise ValueError("La autenticación del proveedor requiere una configuración completa.")

    emitido_en = ahora or datetime.now(timezone.utc)
    payload = {
        "iss": emisor,
        "sub": servicio,
        "aud": audiencia,
        "iat": emitido_en,
        "exp": emitido_en + timedelta(seconds=DURACION_TOKEN_SEGUNDOS),
        "jti": str(uuid.uuid4()),
        "type": "provider_access",
    }
    return jwt.encode(payload, llave_privada, algorithm="RS256")
