"""API de cotizaciones compartida por los canales web, Android y socios."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.enriquecimiento import obtener_consentimientos
from app.api.perfilamiento import obtener_repositorio as obtener_perfiles
from app.cotizaciones.dominio.catalogo import DefinicionRamo, consultar_catalogo_ramos
from app.cotizaciones.dominio.modelos import Cotizacion, RamoSeguro
from app.cotizaciones.dominio.validacion import DatosRiesgoInvalidosError
from app.cotizaciones.repositorio import RepositorioCotizacionesPostgres
from app.cotizaciones.servicio import CotizacionNoEncontrada, ServicioCotizaciones
from app.cotizaciones.servicio_personalizacion import (
    RiesgoNoAsegurableError,
    ServicioPersonalizacionCotizacion,
)
from app.infraestructura.database import get_db
from app.perfilamiento.enriquecimiento.puertos import RepositorioConsentimientos
from app.perfilamiento.repositorio import RepositorioPerfiles

router = APIRouter(prefix="/api/v1/cotizaciones", tags=["cotizaciones"])


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
    servicio: ServicioCotizaciones = Depends(obtener_servicio),
) -> Cotizacion:
    try:
        return servicio.cotizar(
            cliente_id=solicitud.cliente_id,
            ramo=solicitud.ramo,
            datos_riesgo=solicitud.datos_riesgo,
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
    servicio: ServicioCotizaciones = Depends(obtener_servicio),
) -> list[Cotizacion]:
    return servicio.listar_por_cliente(cliente_id)


@router.get(
    "/{cotizacion_id}",
    response_model=Cotizacion,
    summary="Consulta una cotización por su identificador",
    responses={404: {"description": "La cotización solicitada no existe."}},
)
def consultar_cotizacion(
    cotizacion_id: str,
    servicio: ServicioCotizaciones = Depends(obtener_servicio),
) -> Cotizacion:
    try:
        return servicio.consultar(cotizacion_id)
    except CotizacionNoEncontrada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La cotización no existe.",
        ) from None
