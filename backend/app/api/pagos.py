"""API del recaudo inicial de la prima (HU13)."""

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.api.cotizaciones import ActorCotizacion, TipoActorCotizacion, actor_actual
from app.cotizaciones.repositorio import RepositorioCotizacionesPostgres
from app.identidad.modelos import Rol
from app.infraestructura.database import get_db
from app.pagos.modelos import EstadoPago, Pago, SolicitudPago
from app.pagos.pasarela_simulada import PasarelaSimulada
from app.pagos.puertos import PasarelaNoDisponible, PasarelaPagos
from app.pagos.repositorio import RepositorioPagosPostgres
from app.pagos.servicio import (
    CotizacionNoPagable,
    FirmaInvalida,
    LlaveIdempotenciaReutilizada,
    PagoNoEncontrado,
    ServicioPagos,
)

router = APIRouter(prefix="/api/v1/pagos", tags=["pagos"])


def obtener_pasarela() -> PasarelaPagos:
    return PasarelaSimulada()


def obtener_servicio(
    db: Session = Depends(get_db),
    pasarela: PasarelaPagos = Depends(obtener_pasarela),
) -> ServicioPagos:
    return ServicioPagos(
        pagos=RepositorioPagosPostgres(db),
        cotizaciones=RepositorioCotizacionesPostgres(db),
        pasarela=pasarela,
    )


def cliente_pagador(actor: ActorCotizacion = Depends(actor_actual)) -> str:
    if actor.tipo is not TipoActorCotizacion.USUARIO or actor.rol is not Rol.CLIENTE:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo el cliente asegurado puede realizar el pago de su prima.",
        )
    return actor.actor_id


class ConfirmacionPasarela(BaseModel):
    model_config = ConfigDict(extra="ignore")

    referencia: str = Field(min_length=1, max_length=100)
    estado: EstadoPago
    motivo: str | None = Field(default=None, max_length=200)


_ERRORES_NEGOCIO = {
    "COTIZACION_NO_ENCONTRADA": (status.HTTP_404_NOT_FOUND, "La cotización no existe."),
    "COTIZACION_NO_VIGENTE": (status.HTTP_409_CONFLICT, "La cotización no está vigente."),
    "COTIZACION_YA_PAGADA": (status.HTTP_409_CONFLICT, "La cotización ya tiene un pago aprobado."),
    "TOKEN_REQUERIDO": (status.HTTP_422_UNPROCESSABLE_CONTENT, "Falta el token de la tarjeta."),
    "BANCO_REQUERIDO": (status.HTTP_422_UNPROCESSABLE_CONTENT, "Falta el banco para PSE."),
}


@router.post(
    "",
    response_model=Pago,
    response_model_exclude={"huella_solicitud"},
    status_code=status.HTTP_201_CREATED,
    summary="Procesa el recaudo inicial de una cotización",
    description=(
        "Requiere el encabezado Idempotency-Key. Con tarjeta se recibe únicamente el token "
        "emitido por la pasarela; con PSE se devuelve la URL a la que debe redirigirse al "
        "cliente. Un reintento con la misma llave y el mismo cuerpo devuelve el pago original "
        "(200) sin volver a cobrar."
    ),
    responses={
        200: {"description": "Reintento idempotente: se devuelve el pago ya registrado."},
        409: {"description": "Cotización no vigente, ya pagada o llave reutilizada."},
        502: {"description": "La pasarela no respondió; el pago queda PENDIENTE."},
    },
)
def pagar(
    solicitud: SolicitudPago,
    respuesta: Response,
    idempotency_key: str = Header(min_length=8, max_length=64),
    cliente_id: str = Depends(cliente_pagador),
    servicio: ServicioPagos = Depends(obtener_servicio),
) -> Pago:
    try:
        pago, repetido = servicio.pagar(cliente_id, idempotency_key, solicitud)
    except CotizacionNoPagable as error:
        codigo_http, mensaje = _ERRORES_NEGOCIO[error.codigo]
        raise HTTPException(
            codigo_http, detail={"codigo": error.codigo, "mensaje": mensaje}
        ) from None
    except LlaveIdempotenciaReutilizada:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "codigo": "LLAVE_IDEMPOTENCIA_REUTILIZADA",
                "mensaje": "La Idempotency-Key ya se usó con una solicitud distinta.",
            },
        ) from None
    except PasarelaNoDisponible:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={
                "codigo": "PASARELA_NO_DISPONIBLE",
                "mensaje": "La pasarela no respondió. Reintente con la misma Idempotency-Key.",
            },
        ) from None
    if repetido:
        respuesta.status_code = status.HTTP_200_OK
    return pago


@router.get(
    "",
    response_model=list[Pago],
    response_model_exclude={"__all__": {"huella_solicitud"}},
    summary="Lista los pagos del cliente, del más reciente al más antiguo",
)
def listar_pagos(
    cliente_id: str = Depends(cliente_pagador),
    servicio: ServicioPagos = Depends(obtener_servicio),
) -> list[Pago]:
    return servicio.listar(cliente_id)


@router.get(
    "/{pago_id}",
    response_model=Pago,
    response_model_exclude={"huella_solicitud"},
    summary="Consulta el estado de un pago",
)
def consultar_pago(
    pago_id: str,
    cliente_id: str = Depends(cliente_pagador),
    servicio: ServicioPagos = Depends(obtener_servicio),
) -> Pago:
    try:
        return servicio.consultar(pago_id, cliente_id)
    except PagoNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El pago no existe.") from None


@router.post(
    "/confirmaciones",
    status_code=status.HTTP_200_OK,
    summary="Recibe la confirmación aprobado/rechazado de la pasarela",
    description=(
        "Endpoint de la pasarela, sin sesión de usuario. Autentica con HMAC-SHA256 del cuerpo "
        "en X-Firma-Pasarela. Es idempotente: reentregas no cambian un estado final."
    ),
)
async def confirmar_pago(
    request: Request,
    x_firma_pasarela: str | None = Header(default=None),
    servicio: ServicioPagos = Depends(obtener_servicio),
) -> dict[str, str]:
    cuerpo = await request.body()
    try:
        datos = ConfirmacionPasarela.model_validate(json.loads(cuerpo))
    except (ValueError, ValidationError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Confirmación mal formada.") from None

    try:
        pago = servicio.confirmar(
            cuerpo, x_firma_pasarela, datos.referencia, datos.estado, datos.motivo
        )
    except FirmaInvalida:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Firma inválida.") from None
    except PagoNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pago desconocido.") from None
    return {"pago_id": pago.pago_id, "estado": pago.estado.value}
