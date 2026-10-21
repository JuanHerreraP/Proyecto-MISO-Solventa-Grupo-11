"""API de cotizaciones compartida por los canales web, Android y socios."""

from enum import Enum

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.enriquecimiento import obtener_consentimientos
from app.api.perfilamiento import obtener_repositorio as obtener_perfiles
from app.api.seguridad import get_current_user
from app.api.seguridad_socios import socio_actual
from app.api.socios import obtener_servicio as obtener_servicio_socios
from app.cotizaciones.dominio.catalogo import DefinicionRamo, consultar_catalogo_ramos
from app.cotizaciones.dominio.modelos import Cotizacion, RamoSeguro
from app.cotizaciones.dominio.validacion import DatosRiesgoInvalidosError
from app.cotizaciones.repositorio import RepositorioCotizacionesPostgres
from app.cotizaciones.servicio import CotizacionNoEncontrada, ServicioCotizaciones
from app.cotizaciones.servicio_personalizacion import (
    RiesgoNoAsegurableError,
    ServicioPersonalizacionCotizacion,
)
from app.identidad.modelos import Rol
from app.infraestructura.database import get_db
from app.perfilamiento.enriquecimiento.puertos import RepositorioConsentimientos
from app.perfilamiento.repositorio import RepositorioPerfiles
from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.servicio import (
    CredencialesSocioInvalidas,
    EndpointNoAutorizado,
    ServicioSocios,
    SocioInactivo,
)

router = APIRouter(prefix="/api/v1/cotizaciones", tags=["cotizaciones"])
bearer_cotizaciones = HTTPBearer(auto_error=False)


class TipoActorCotizacion(str, Enum):
    USUARIO = "USUARIO"
    SOCIO = "SOCIO"


class ActorCotizacion(BaseModel):
    tipo: TipoActorCotizacion
    actor_id: str
    rol: Rol | None = None
    socio_id: str | None = None
    tenant_id: str | None = None
    scopes: set[CodigoEndpoint] = Field(default_factory=set)


def actor_actual(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_cotizaciones),
    db: Session = Depends(get_db),
) -> ActorCotizacion:
    if credentials is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Se requiere autenticación.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        tipo_token = jwt.decode(
            credentials.credentials,
            options={"verify_signature": False},
        ).get("type")
    except jwt.InvalidTokenError:
        tipo_token = None

    if tipo_token == "partner_access":
        identidad = socio_actual(request, credentials)
        return ActorCotizacion(
            tipo=TipoActorCotizacion.SOCIO,
            actor_id=identidad.client_id,
            socio_id=identidad.socio_id,
            tenant_id=identidad.tenant_id,
            scopes=identidad.scopes,
        )

    usuario = get_current_user(request, credentials, db)
    try:
        rol = Rol(usuario.rol)
    except ValueError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El usuario tiene un rol no reconocido.",
        ) from None
    return ActorCotizacion(
        tipo=TipoActorCotizacion.USUARIO,
        actor_id=str(usuario.id),
        rol=rol,
    )


def creador_actual(
    actor: ActorCotizacion = Depends(actor_actual),
    socios: ServicioSocios = Depends(obtener_servicio_socios),
) -> ActorCotizacion:
    if actor.tipo is TipoActorCotizacion.SOCIO:
        if actor.socio_id is None or actor.tenant_id is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Las credenciales del socio no son válidas.",
            )
        if CodigoEndpoint.COTIZACIONES_CREAR not in actor.scopes:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "El socio no tiene permiso para crear cotizaciones.",
            )
        try:
            socios.autorizar_consumo(
                actor.socio_id,
                actor.tenant_id,
                CodigoEndpoint.COTIZACIONES_CREAR,
            )
        except CredencialesSocioInvalidas:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Las credenciales del socio no son válidas.",
            ) from None
        except (SocioInactivo, EndpointNoAutorizado):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "El socio no está autorizado para crear cotizaciones.",
            ) from None
        return actor

    if actor.rol not in {Rol.CLIENTE, Rol.ASESOR_VENTAS, Rol.SERVICIO_INTERNO}:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El usuario no tiene permiso para crear cotizaciones.",
        )
    return actor


def lector_actual(
    actor: ActorCotizacion = Depends(actor_actual),
) -> ActorCotizacion:
    if actor.tipo is TipoActorCotizacion.SOCIO or actor.rol not in {
        Rol.CLIENTE,
        Rol.ASESOR_VENTAS,
        Rol.SERVICIO_INTERNO,
    }:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El actor no tiene permiso para consultar cotizaciones.",
        )
    return actor


class SolicitudCotizacion(BaseModel):
    """Contrato neutral utilizado por aplicaciones y socios de distribución."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "cliente_id": "CLI-001",
                "ramo": "VIAJE",
                "datos_riesgo": {
                    "destino": "Lima",
                    "fecha_inicio": "2027-01-10",
                    "fecha_fin": "2027-01-20",
                    "numero_viajeros": 2,
                    "valor_asegurado": 15000000,
                },
            }
        },
    )

    cliente_id: str = Field(min_length=1, max_length=50)
    ramo: RamoSeguro
    datos_riesgo: dict[str, object]


def obtener_servicio(
    db: Session = Depends(get_db),
    perfiles: RepositorioPerfiles = Depends(obtener_perfiles),
    consentimientos: RepositorioConsentimientos = Depends(obtener_consentimientos),
) -> ServicioCotizaciones:
    return ServicioCotizaciones(
        repositorio=RepositorioCotizacionesPostgres(db),
        personalizador=ServicioPersonalizacionCotizacion(
            perfiles=perfiles,
            consentimientos=consentimientos,
        ),
    )


@router.get(
    "/ramos",
    response_model=list[DefinicionRamo],
    summary="Consulta los ramos disponibles y sus datos requeridos",
    description=(
        "Contrato común para construir formularios de cotización en web, Android "
        "o canales de socios."
    ),
)
def consultar_ramos() -> tuple[DefinicionRamo, ...]:
    return consultar_catalogo_ramos()


@router.post(
    "",
    response_model=Cotizacion,
    status_code=status.HTTP_201_CREATED,
    summary="Calcula y almacena una cotización de seguro",
    description=(
        "Recibe el mismo contrato desde web, Android o un socio de distribución. "
        "Valida los datos del ramo, calcula la prima y aplica un perfil autorizado "
        "cuando se encuentra disponible."
    ),
    responses={
        409: {"description": "El perfil vigente no permite ofrecer la cobertura."},
        422: {"description": "Los datos requeridos por el ramo no son válidos."},
    },
)
def crear_cotizacion(
    solicitud: SolicitudCotizacion,
    actor: ActorCotizacion = Depends(creador_actual),
    servicio: ServicioCotizaciones = Depends(obtener_servicio),
) -> Cotizacion:
    if actor.rol is Rol.CLIENTE and actor.actor_id != solicitud.cliente_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El cliente solo puede crear cotizaciones para sí mismo.",
        )

    try:
        return servicio.cotizar(
            cliente_id=solicitud.cliente_id,
            ramo=solicitud.ramo,
            datos_riesgo=solicitud.datos_riesgo,
            asesor_id=(
                actor.actor_id
                if actor.tipo is TipoActorCotizacion.USUARIO and actor.rol is Rol.ASESOR_VENTAS
                else None
            ),
            socio_id=actor.socio_id,
            tenant_id=actor.tenant_id,
        )
    except DatosRiesgoInvalidosError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "codigo": "DATOS_RIESGO_INVALIDOS",
                "mensaje": str(error),
                "errores": [detalle.model_dump(mode="json") for detalle in error.errores],
            },
        ) from None
    except RiesgoNoAsegurableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "codigo": "RIESGO_NO_ASEGURABLE",
                "mensaje": "El perfil vigente no permite ofrecer esta cobertura.",
            },
        ) from None


@router.get(
    "",
    response_model=list[Cotizacion],
    summary="Lista las cotizaciones de un cliente",
)
def listar_cotizaciones(
    cliente_id: str = Query(min_length=1, max_length=50),
    actor: ActorCotizacion = Depends(lector_actual),
    servicio: ServicioCotizaciones = Depends(obtener_servicio),
) -> list[Cotizacion]:
    if actor.rol is Rol.CLIENTE and actor.actor_id != cliente_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El cliente solo puede consultar sus propias cotizaciones.",
        )

    cotizaciones = servicio.listar_por_cliente(cliente_id)
    if actor.rol is Rol.ASESOR_VENTAS:
        return [cotizacion for cotizacion in cotizaciones if cotizacion.asesor_id == actor.actor_id]
    return cotizaciones


@router.get(
    "/{cotizacion_id}",
    response_model=Cotizacion,
    summary="Consulta una cotización por su identificador",
    responses={404: {"description": "La cotización solicitada no existe."}},
)
def consultar_cotizacion(
    cotizacion_id: str,
    actor: ActorCotizacion = Depends(lector_actual),
    servicio: ServicioCotizaciones = Depends(obtener_servicio),
) -> Cotizacion:
    try:
        cotizacion = servicio.consultar(cotizacion_id)
    except CotizacionNoEncontrada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La cotización no existe.",
        ) from None

    if actor.rol is Rol.CLIENTE and cotizacion.cliente_id != actor.actor_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El cliente solo puede consultar sus propias cotizaciones.",
        )
    if actor.rol is Rol.ASESOR_VENTAS and cotizacion.asesor_id != actor.actor_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El asesor solo puede consultar sus procesos asistidos.",
        )
    return cotizacion
