"""API del enriquecimiento del perfil con Open Finance y Open Data (HU10)."""

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.perfilamiento import obtener_servicio as obtener_servicio_perfilamiento
from app.api.seguridad import Rol, requiere_roles, verificar_propietario
from app.perfilamiento.dominio.modelos import Dictamen
from app.perfilamiento.enriquecimiento.configuracion import crear_servicio
from app.perfilamiento.enriquecimiento.memoria import RepositorioConsentimientosEnMemoria
from app.perfilamiento.enriquecimiento.modelos import Consentimiento, ResultadoEnriquecimiento
from app.perfilamiento.enriquecimiento.puertos import RepositorioConsentimientos
from app.perfilamiento.enriquecimiento.servicio import (
    EnriquecimientoNoDisponible,
    ServicioEnriquecimiento,
    SinConsentimientoVigente,
)
from app.perfilamiento.servicio import ServicioPerfilamiento

router = APIRouter(prefix="/api/v1", tags=["enriquecimiento"])

ROLES_QUE_INICIAN = {Rol.ASESOR_VENTAS, Rol.SERVICIO_INTERNO}
ROLES_QUE_CONSULTAN = {Rol.ANALISTA_RIESGOS, Rol.SERVICIO_INTERNO}
ROLES_QUE_REGISTRAN_CONSENTIMIENTO = {Rol.CLIENTE, Rol.ASESOR_VENTAS, Rol.SERVICIO_INTERNO}


registrador_actual = requiere_roles(*ROLES_QUE_REGISTRAN_CONSENTIMIENTO)
iniciador_actual = requiere_roles(*ROLES_QUE_INICIAN)
consultor_actual = requiere_roles(*ROLES_QUE_CONSULTAN)


@lru_cache
def obtener_consentimientos() -> RepositorioConsentimientos:
    return RepositorioConsentimientosEnMemoria()


@lru_cache
def obtener_servicio() -> ServicioEnriquecimiento:
    return crear_servicio(consentimientos=obtener_consentimientos())


class SolicitudEnriquecimiento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cliente_id: str = Field(min_length=1)
    cotizacion_id: str = Field(min_length=1, description="Proceso de cotización autorizado.")


class RespuestaEnriquecimiento(BaseModel):
    enriquecimiento: ResultadoEnriquecimiento
    perfil_id: str
    dictamen: Dictamen


@router.post(
    "/consentimientos",
    response_model=Consentimiento,
    status_code=status.HTTP_201_CREATED,
    summary="Registra el consentimiento del cliente (provisional)",
    description=(
        "PROVISIONAL: el consentimiento pertenece al servicio de Identidad, KYC y "
        "Consentimiento. Este endpoint existe para poder ejercitar el flujo mientras ese "
        "servicio no esté disponible."
    ),
)
def registrar_consentimiento(
    consentimiento: Consentimiento,
    usuario=Depends(registrador_actual),
    consentimientos: RepositorioConsentimientos = Depends(obtener_consentimientos),
) -> Consentimiento:
    verificar_propietario(consentimiento.cliente_id, usuario)
    consentimientos.registrar(consentimiento)
    return consentimiento


@router.post(
    "/enriquecimientos",
    response_model=RespuestaEnriquecimiento,
    status_code=status.HTTP_201_CREATED,
    summary="Consulta las fuentes externas, consolida las señales y genera el perfil de riesgo",
)
async def enriquecer(
    solicitud: SolicitudEnriquecimiento,
    usuario=Depends(iniciador_actual),
    servicio: ServicioEnriquecimiento = Depends(obtener_servicio),
    perfilamiento: ServicioPerfilamiento = Depends(obtener_servicio_perfilamiento),
) -> RespuestaEnriquecimiento:
    try:
        resultado = await servicio.enriquecer(solicitud.cliente_id, solicitud.cotizacion_id)
    except SinConsentimientoVigente:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "El cliente no tiene un consentimiento vigente."
        ) from None
    except EnriquecimientoNoDisponible as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"La fuente {error.tipo.value} no está disponible y no hay datos en caché.",
        ) from None

    perfil = perfilamiento.generar_perfil(resultado.senales)
    return RespuestaEnriquecimiento(
        enriquecimiento=resultado, perfil_id=perfil.perfil_id, dictamen=perfil.dictamen
    )


@router.get(
    "/enriquecimientos/{cliente_id}",
    response_model=ResultadoEnriquecimiento,
    summary="Consulta las señales consolidadas y su trazabilidad",
)
def consultar_enriquecimiento(
    cliente_id: str,
    usuario=Depends(consultor_actual),
    servicio: ServicioEnriquecimiento = Depends(obtener_servicio),
) -> ResultadoEnriquecimiento:
    resultado = servicio.ultimo(cliente_id)
    if resultado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay señales para el cliente.")
    return resultado
