"""Generación de tokens JWT para autenticación."""

import os
import uuid
from dataclasses import dataclass
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

ACCESS_TOKEN_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "30"))

REFRESH_TOKEN_DAYS = int(
    os.getenv(
        "JWT_REFRESH_TOKEN_DAYS",
        "7",
    )
)


def crear_access_token(
    usuario_id: str,
    email: str,
    rol: str,
    sesion_id: str | None = None,
) -> str:

    ahora = datetime.now(timezone.utc)
    expiracion = ahora + timedelta(minutes=ACCESS_TOKEN_MINUTES)

    payload = {
        "sub": usuario_id,
        "email": email,
        "rol": rol,
        "iat": ahora,
        "exp": expiracion,
        "type": "access",
    }

    private_key = PRIVATE_KEY_PATH.read_text()

    if sesion_id is not None:
        payload["sid"] = sesion_id

    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
    )


class TokenExpiradoError(Exception):
    pass


class TokenInvalidoError(Exception):
    pass


def validar_access_token(
    token: str,
) -> dict:

    public_key = PUBLIC_KEY_PATH.read_text()

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
        )

    except jwt.ExpiredSignatureError as error:
        raise TokenExpiradoError("El token de acceso ha expirado.") from error

    except jwt.InvalidTokenError as error:
        raise TokenInvalidoError("El token de acceso no es válido.") from error

    if payload.get("type") != "access":
        raise TokenInvalidoError("El token proporcionado no es un token de acceso.")

    if not payload.get("sub"):
        raise TokenInvalidoError("El token no contiene un usuario válido.")

    return payload


@dataclass(frozen=True)
class RefreshTokenEmitido:
    """Refresh token firmado junto con su identificador único (jti)."""

    token: str
    jti: str
    expira_en: datetime


def emitir_refresh_token(
    usuario_id: str,
    email: str,
    rol: str,
) -> RefreshTokenEmitido:
    """Emite un refresh token con un `jti` único para poder rotarlo y revocarlo."""

    ahora = datetime.now(timezone.utc)
    expiracion = ahora + timedelta(days=REFRESH_TOKEN_DAYS)
    jti = str(uuid.uuid4())

    payload = {
        "sub": usuario_id,
        "email": email,
        "rol": rol,
        "iat": ahora,
        "exp": expiracion,
        "type": "refresh",
        "jti": jti,
    }

    private_key = PRIVATE_KEY_PATH.read_text()

    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
    )

    return RefreshTokenEmitido(token=token, jti=jti, expira_en=expiracion)


def crear_refresh_token(
    usuario_id: str,
    email: str,
    rol: str,
) -> str:
    return emitir_refresh_token(usuario_id=usuario_id, email=email, rol=rol).token


def validar_refresh_token(
    token: str,
) -> dict:

    public_key = PUBLIC_KEY_PATH.read_text()

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
        )

    except jwt.ExpiredSignatureError as error:
        raise TokenExpiradoError("El refresh token ha expirado.") from error

    except jwt.InvalidTokenError as error:
        raise TokenInvalidoError("El refresh token no es válido.") from error

    if payload.get("type") != "refresh":
        raise TokenInvalidoError("El token proporcionado no es un refresh token.")

    return payload
