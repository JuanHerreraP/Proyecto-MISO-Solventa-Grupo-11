"""Generación de tokens JWT para autenticación."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt


BASE_DIR = Path(__file__).resolve().parents[2]

PRIVATE_KEY_PATH = Path(
    os.getenv(
        "JWT_PRIVATE_KEY_PATH",
        str(BASE_DIR / "keys" / "private_key.pem"),
    )
)

PUBLIC_KEY_PATH = Path(
    os.getenv(
        "JWT_PUBLIC_KEY_PATH",
        str(BASE_DIR / "keys" / "public_key.pem"),
    )
)

ACCESS_TOKEN_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_MINUTES", "30")
)


def crear_access_token(
    usuario_id: str,
    email: str,
    rol: str,
) -> str:

    ahora = datetime.now(timezone.utc)
    expiracion = ahora + timedelta(
        minutes=ACCESS_TOKEN_MINUTES
    )

    payload = {
        "sub": usuario_id,
        "email": email,
        "rol": rol,
        "iat": ahora,
        "exp": expiracion,
        "type": "access",
    }

    private_key = PRIVATE_KEY_PATH.read_text()

    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
    )