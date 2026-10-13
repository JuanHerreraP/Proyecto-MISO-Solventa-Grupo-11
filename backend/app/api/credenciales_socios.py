"""API administrativa para aprovisionar credenciales de socios."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.socios import administrador_actual
from app.infraestructura.database import get_db
from app.socios.dominio.credenciales import CredencialesEmitidas
from app.socios.repositorio import RepositorioSociosPostgres
from app.socios.repositorio_credenciales import RepositorioCredencialesSociosPostgres
from app.socios.servicio import SocioInactivo, SocioNoEncontrado
from app.socios.servicio_credenciales import ServicioCredencialesSocios

router = APIRouter(prefix="/api/v1/socios", tags=["credenciales de socios"])


def obtener_servicio_credenciales(
    db: Session = Depends(get_db),
) -> ServicioCredencialesSocios:
    return ServicioCredencialesSocios(
        socios=RepositorioSociosPostgres(db),
        credenciales=RepositorioCredencialesSociosPostgres(db),
    )


@router.post(
    "/{socio_id}/credenciales",
    response_model=CredencialesEmitidas,
    status_code=status.HTTP_201_CREATED,
    summary="Aprovisiona credenciales estándar para un socio",
)
def aprovisionar_credenciales(
    socio_id: str,
    _usuario=Depends(administrador_actual),
    servicio: ServicioCredencialesSocios = Depends(obtener_servicio_credenciales),
) -> CredencialesEmitidas:
    """Entrega el secreto únicamente como parte de la respuesta de creación."""

    try:
        return servicio.aprovisionar(socio_id)
    except SocioNoEncontrado:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "El socio no existe.",
        ) from None
    except SocioInactivo:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El socio debe estar activo para generar credenciales.",
        ) from None
