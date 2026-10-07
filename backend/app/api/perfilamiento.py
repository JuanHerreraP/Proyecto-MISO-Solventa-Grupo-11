"""API del perfil de riesgo individualizado (HU11)."""

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.seguridad import Rol, rol_actual
from app.perfilamiento.dominio.modelos import OfertaCliente, PerfilRiesgo, SenalesPerfilamiento
from app.perfilamiento.repositorio import RepositorioPerfilesEnMemoria
from app.perfilamiento.servicio import (
    ConsentimientoNoVigente,
    ServicioPerfilamiento,
    a_oferta_cliente,
)

router = APIRouter(prefix="/api/v1/perfiles-riesgo", tags=["perfilamiento"])

ROLES_QUE_GENERAN = {Rol.SERVICIO_INTERNO, Rol.ASESOR_VENTAS}
ROLES_QUE_VEN_EL_DETALLE = {Rol.ANALISTA_RIESGOS, Rol.SERVICIO_INTERNO}


@lru_cache
def obtener_servicio() -> ServicioPerfilamiento:
    return ServicioPerfilamiento(RepositorioPerfilesEnMemoria())


@router.post(
    "",
    response_model=PerfilRiesgo,
    status_code=status.HTTP_201_CREATED,
    summary="Genera el perfil de riesgo y el dictamen de suscripción",
)
def generar_perfil(
    senales: SenalesPerfilamiento,
    rol: Rol = Depends(rol_actual),
    servicio: ServicioPerfilamiento = Depends(obtener_servicio),
) -> PerfilRiesgo:
    if rol not in ROLES_QUE_GENERAN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El rol no puede generar perfiles.")
    try:
        return servicio.generar_perfil(senales)
    except ConsentimientoNoVigente:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El cliente no tiene un consentimiento vigente.",
        ) from None


@router.get(
    "/{cliente_id}",
    response_model=PerfilRiesgo,
    summary="Consulta el perfil completo, con el puntaje y las reglas aplicadas",
)
def consultar_perfil(
    cliente_id: str,
    rol: Rol = Depends(rol_actual),
    servicio: ServicioPerfilamiento = Depends(obtener_servicio),
) -> PerfilRiesgo:
    if rol not in ROLES_QUE_VEN_EL_DETALLE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El rol no puede ver el detalle del perfil.")
    perfil = servicio.consultar_perfil(cliente_id)
    if perfil is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay un perfil vigente para el cliente.")
    return perfil


@router.get(
    "/{cliente_id}/oferta",
    response_model=OfertaCliente,
    summary="Consulta la oferta y su explicación, sin reglas internas",
)
def consultar_oferta(
    cliente_id: str,
    rol: Rol = Depends(rol_actual),
    servicio: ServicioPerfilamiento = Depends(obtener_servicio),
) -> OfertaCliente:
    perfil = servicio.consultar_perfil(cliente_id)
    if perfil is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay un perfil vigente para el cliente.")
    return a_oferta_cliente(perfil)
