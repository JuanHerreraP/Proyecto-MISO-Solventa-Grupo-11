"""API de administración de socios de distribución (HU24)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.seguridad import requiere_roles
from app.identidad.modelos import Rol
from app.infraestructura.database import get_db
from app.socios.dominio.modelos import (
    SocioDistribucion,
    SolicitudActualizacionSocio,
    SolicitudAltaSocio,
)
from app.socios.dominio.tenant import AprovisionadorTenantsEnMemoria
from app.socios.repositorio import (
    RepositorioAuditoriaSociosPostgres,
    RepositorioSociosPostgres,
)
from app.socios.servicio import NitDuplicado, ServicioSocios, SocioNoEncontrado

router = APIRouter(prefix="/api/v1/socios", tags=["socios"])

ROLES_ADMINISTRADORES = (
    Rol.INGENIERO_INTEGRACIONES.value,
    Rol.SERVICIO_INTERNO.value,
)
administrador_actual = requiere_roles(*ROLES_ADMINISTRADORES)


def obtener_servicio(db: Session = Depends(get_db)) -> ServicioSocios:
    return ServicioSocios(
        repositorio=RepositorioSociosPostgres(db),
        tenants=AprovisionadorTenantsEnMemoria(),
        auditoria=RepositorioAuditoriaSociosPostgres(db),
    )


@router.post(
    "",
    response_model=SocioDistribucion,
    status_code=status.HTTP_201_CREATED,
    summary="Registra y aprovisiona un socio de distribución",
)
def dar_de_alta(
    solicitud: SolicitudAltaSocio,
    usuario=Depends(administrador_actual),
    servicio: ServicioSocios = Depends(obtener_servicio),
) -> SocioDistribucion:
    try:
        return servicio.dar_de_alta(solicitud, str(usuario.id))
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
    _usuario=Depends(administrador_actual),
    servicio: ServicioSocios = Depends(obtener_servicio),
) -> SocioDistribucion:
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
    usuario=Depends(administrador_actual),
    servicio: ServicioSocios = Depends(obtener_servicio),
) -> SocioDistribucion:
    try:
        return servicio.actualizar(socio_id, solicitud, str(usuario.id))
    except SocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El socio no existe.") from None
