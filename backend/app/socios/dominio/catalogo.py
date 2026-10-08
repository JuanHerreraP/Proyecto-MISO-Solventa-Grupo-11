"""Catálogo estándar de endpoints disponibles para socios (BPM-144)."""

from enum import Enum

from pydantic import BaseModel, ConfigDict


class MetodoHttp(str, Enum):
    POST = "POST"


class CodigoEndpoint(str, Enum):
    COTIZACIONES_CREAR = "cotizaciones:crear"
    POLIZAS_EMITIR = "polizas:emitir"


class EndpointSocio(BaseModel):
    """Contrato que un socio puede solicitar durante su alta."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    codigo: CodigoEndpoint
    metodo: MetodoHttp
    ruta: str
    descripcion: str


CATALOGO_ENDPOINTS: tuple[EndpointSocio, ...] = (
    EndpointSocio(
        codigo=CodigoEndpoint.COTIZACIONES_CREAR,
        metodo=MetodoHttp.POST,
        ruta="/api/v1/cotizaciones",
        descripcion="Solicitar una cotización de seguro.",
    ),
    EndpointSocio(
        codigo=CodigoEndpoint.POLIZAS_EMITIR,
        metodo=MetodoHttp.POST,
        ruta="/api/v1/polizas",
        descripcion="Emitir la póliza de una cotización aceptada.",
    ),
)


def consultar_catalogo() -> tuple[EndpointSocio, ...]:
    """Retorna los contratos que pueden asignarse a un socio."""

    return CATALOGO_ENDPOINTS
