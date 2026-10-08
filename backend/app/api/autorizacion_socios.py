"""Autorización provisional de socios para el gateway (BPM-147)."""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.api.socios import obtener_servicio
from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.servicio import (
    CredencialesSocioInvalidas,
    EndpointNoAutorizado,
    ServicioSocios,
    SocioInactivo,
)

router = APIRouter(prefix="/api/v1/autorizaciones", tags=["autorización de socios"])


class AutorizacionConcedida(BaseModel):
    autorizado: bool
    socio_id: str
    tenant_id: str
    scope: CodigoEndpoint


@router.post(
    "/socios",
    response_model=AutorizacionConcedida,
    summary="Valida el tenant y el scope configurado para un socio",
)
def autorizar_socio(
    x_socio_id: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    x_scope: str | None = Header(default=None),
    servicio: ServicioSocios = Depends(obtener_servicio),
) -> AutorizacionConcedida:
    """Contrato interno para el gateway hasta que HU19 entregue credenciales firmadas."""

    if not x_socio_id or not x_tenant_id:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Faltan las credenciales del socio.",
        )
    try:
        endpoint = CodigoEndpoint(x_scope)
    except (TypeError, ValueError):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El scope solicitado no está autorizado.",
        ) from None

    try:
        socio = servicio.autorizar_consumo(x_socio_id, x_tenant_id, endpoint)
    except CredencialesSocioInvalidas:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Las credenciales del socio no son válidas.",
        ) from None
    except SocioInactivo:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El socio no se encuentra activo.",
        ) from None
    except EndpointNoAutorizado:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El scope solicitado no está autorizado.",
        ) from None

    return AutorizacionConcedida(
        autorizado=True,
        socio_id=socio.socio_id,
        tenant_id=socio.tenant_id,
        scope=endpoint,
    )
