"""API de administración de socios de distribución (HU24)."""

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.seguridad import Rol, actor_actual, rol_actual
from app.socios.dominio.auditoria import RepositorioAuditoriaSociosEnMemoria
from app.socios.dominio.modelos import (
    SocioDistribucion,
    SolicitudActualizacionSocio,
    SolicitudAltaSocio,
)
from app.socios.dominio.tenant import AprovisionadorTenantsEnMemoria
from app.socios.repositorio import RepositorioSociosEnMemoria
from app.socios.servicio import NitDuplicado, ServicioSocios, SocioNoEncontrado

router = APIRouter(prefix="/api/v1/socios", tags=["socios"])

ROLES_ADMINISTRADORES = {Rol.INGENIERO_INTEGRACIONES, Rol.SERVICIO_INTERNO}


@lru_cache
def obtener_servicio() -> ServicioSocios:
    return ServicioSocios(
        repositorio=RepositorioSociosEnMemoria(),
        tenants=AprovisionadorTenantsEnMemoria(),
        auditoria=RepositorioAuditoriaSociosEnMemoria(),
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
    actor_id: str = Depends(actor_actual),
    servicio: ServicioSocios = Depends(obtener_servicio),
) -> SocioDistribucion:
    if rol not in ROLES_ADMINISTRADORES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El rol no puede registrar socios.")
    try:
        return servicio.dar_de_alta(solicitud, actor_id)
    except NitDuplicado:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ya existe un socio registrado con el mismo NIT.",
        ) from None


@router.get(
    "/{socio_id}",
    response_model=SocioDistribucion,
    summary="Consulta la configuración de un socio",
)
def consultar(
    socio_id: str,
    rol: Rol = Depends(rol_actual),
    servicio: ServicioSocios = Depends(obtener_servicio),
) -> SocioDistribucion:
    if rol not in ROLES_ADMINISTRADORES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El rol no puede consultar socios.")
    try:
        return servicio.consultar(socio_id)
    except SocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El socio no existe.") from None


@router.patch(
    "/{socio_id}",
    response_model=SocioDistribucion,
    summary="Modifica la configuración de un socio",
)
def actualizar(
    socio_id: str,
    solicitud: SolicitudActualizacionSocio,
    rol: Rol = Depends(rol_actual),
    actor_id: str = Depends(actor_actual),
    servicio: ServicioSocios = Depends(obtener_servicio),
) -> SocioDistribucion:
    if rol not in ROLES_ADMINISTRADORES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El rol no puede modificar socios.")
    try:
        return servicio.actualizar(socio_id, solicitud, actor_id)
    except SocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El socio no existe.") from None
