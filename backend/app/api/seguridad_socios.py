"""Validación de tokens Bearer utilizados por integraciones de socios."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError

from app.identidad.tokens import TokenExpiradoError, TokenInvalidoError
from app.socios.dominio.credenciales import SocioAutenticado
from app.socios.tokens import validar_access_token_socio

bearer_socio = HTTPBearer(auto_error=False)


def socio_actual(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_socio),
) -> SocioAutenticado:
    if credentials is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Se requiere un token de socio.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = validar_access_token_socio(credentials.credentials)
        return SocioAutenticado(
            client_id=payload["sub"],
            socio_id=payload["socio_id"],
            tenant_id=payload["tenant_id"],
            scopes=set(payload["scope"]),
        )
    except TokenExpiradoError as error:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except (TokenInvalidoError, ValidationError, TypeError) as error:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "El token del socio no es válido.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
