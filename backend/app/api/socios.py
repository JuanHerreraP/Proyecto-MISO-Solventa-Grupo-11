"""API de administración de socios de distribución (BPM-143)."""

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.seguridad import Rol, rol_actual
from app.socios.dominio.modelos import SocioDistribucion, SolicitudAltaSocio
from app.socios.dominio.tenant import AprovisionadorTenantsEnMemoria
from app.socios.repositorio import RepositorioSociosEnMemoria
from app.socios.servicio import NitDuplicado, ServicioSocios

router = APIRouter(prefix="/api/v1/socios", tags=["socios"])

ROLES_QUE_DAN_ALTA = {Rol.INGENIERO_INTEGRACIONES, Rol.SERVICIO_INTERNO}


@lru_cache
def obtener_servicio() -> ServicioSocios:
    return ServicioSocios(
        repositorio=RepositorioSociosEnMemoria(),
        tenants=AprovisionadorTenantsEnMemoria(),
    )


@router.post(
    "",
    response_model=SocioDistribucion,
    status_code=status.HTTP_201_CREATED,
    summary="Registra y aprovisiona un socio de distribución",
)
def dar_de_alta(
    solicitud: SolicitudAltaSocio,
    rol: Rol = Depends(rol_actual),
    servicio: ServicioSocios = Depends(obtener_servicio),
) -> SocioDistribucion:
    if rol not in ROLES_QUE_DAN_ALTA:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El rol no puede registrar socios.")
    try:
        return servicio.dar_de_alta(solicitud)
    except NitDuplicado:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ya existe un socio registrado con el mismo NIT.",
        ) from None
