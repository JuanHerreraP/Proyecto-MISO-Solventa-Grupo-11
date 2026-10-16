"""Endpoint OAuth para integraciones entre socios y Solventa."""

from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from app.infraestructura.database import get_db
from app.socios.dominio.credenciales import TokenAccesoSocio
from app.socios.repositorio import RepositorioSociosPostgres
from app.socios.repositorio_credenciales import RepositorioCredencialesSociosPostgres
from app.socios.servicio_autenticacion import (
    CredencialesIntegracionInvalidas,
    ServicioAutenticacionSocios,
    SocioIntegracionInactivo,
)

router = APIRouter(prefix="/api/v1/oauth", tags=["OAuth socios"])
basic = HTTPBasic(auto_error=False)


def obtener_servicio_autenticacion_socios(
    db: Session = Depends(get_db),
) -> ServicioAutenticacionSocios:
    return ServicioAutenticacionSocios(
        socios=RepositorioSociosPostgres(db),
        credenciales=RepositorioCredencialesSociosPostgres(db),
    )


@router.post(
    "/token",
    response_model=TokenAccesoSocio,
    summary="Intercambia credenciales de un socio por un token",
)
async def emitir_token(
    request: Request,
    credenciales_http: HTTPBasicCredentials | None = Depends(basic),
    servicio: ServicioAutenticacionSocios = Depends(obtener_servicio_autenticacion_socios),
) -> TokenAccesoSocio:
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" not in content_type:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "El contenido debe usar application/x-www-form-urlencoded.",
        )

    formulario = parse_qs((await request.body()).decode("utf-8"))
    if formulario.get("grant_type") != ["client_credentials"]:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "El grant_type debe ser client_credentials.",
        )
    if credenciales_http is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Se requieren las credenciales del socio.",
            headers={"WWW-Authenticate": "Basic"},
        )

    try:
        return servicio.autenticar(
            credenciales_http.username,
            credenciales_http.password,
        )
    except CredencialesIntegracionInvalidas:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Las credenciales del socio no son válidas.",
            headers={"WWW-Authenticate": "Basic"},
        ) from None
    except SocioIntegracionInactivo:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El socio no se encuentra activo.",
        ) from None
