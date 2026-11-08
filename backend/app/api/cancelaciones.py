"""API de cancelación de la póliza (HU22 / BPM-35).

Flujo de la app: consultar las condiciones (consecuencias, motivos y saldo a favor estimado) y
confirmar. Cancelar es inmediato e irreversible. Cancela el cliente titular o el asesor de la
venta asistida.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.cotizaciones import ActorCotizacion, TipoActorCotizacion, actor_actual
from app.cotizaciones.repositorio import RepositorioCotizacionesPostgres
from app.desembolsos.repositorio import RepositorioDesembolsosPostgres
from app.infraestructura.database import get_db
from app.polizas.cancelacion import ServicioCancelaciones
from app.polizas.dominio.cancelacion import (
    CancelacionNoPermitida,
    ConfirmacionRequerida,
    SolicitudCancelacion,
)
from app.polizas.emision import AccesoDenegado
from app.polizas.endosos import (
    ROLES_QUE_MODIFICAN,
    ClaveIdempotenciaReutilizada,
    Solicitante,
)
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.polizas.repositorio_cancelaciones import RepositorioCancelacionesPostgres
from app.polizas.repositorio_renovaciones import RepositorioRenovacionesPostgres
from app.polizas.servicio import PolizaNoEncontrada
from app.polizas.vistas_cancelacion import (
    CancelacionVista,
    CondicionesCancelacion,
    a_cancelacion,
    a_condiciones,
)
from app.siniestros.repositorio import RepositorioSiniestrosPostgres

router = APIRouter(prefix="/api/v1/polizas", tags=["cancelaciones"])


def obtener_servicio(db: Session = Depends(get_db)) -> ServicioCancelaciones:
    return ServicioCancelaciones(
        polizas=RepositorioPolizasPostgres(db),
        cancelaciones=RepositorioCancelacionesPostgres(db),
        siniestros=RepositorioSiniestrosPostgres(db),
        desembolsos=RepositorioDesembolsosPostgres(db),
        cotizaciones=RepositorioCotizacionesPostgres(db),
        renovaciones=RepositorioRenovacionesPostgres(db),
    )


def solicitante_actual(
    request: Request, actor: ActorCotizacion = Depends(actor_actual)
) -> Solicitante:
    if (
        actor.tipo is not TipoActorCotizacion.USUARIO
        or actor.rol is None
        or actor.rol not in ROLES_QUE_MODIFICAN
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "El actor no tiene permiso para gestionar pólizas."
        )
    return Solicitante(
        actor_id=actor.actor_id,
        rol=actor.rol,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


def _error(codigo: str, mensaje: str, **extra: object) -> dict[str, object]:
    return {"codigo": codigo, "mensaje": mensaje, **extra}


def _traducir(error: Exception) -> HTTPException:
    if isinstance(error, PolizaNoEncontrada):
        return HTTPException(
            status.HTTP_404_NOT_FOUND, _error("POLIZA_NO_ENCONTRADA", "La póliza no existe.")
        )
    if isinstance(error, AccesoDenegado):
        return HTTPException(
            status.HTTP_403_FORBIDDEN,
            _error(
                "ACCESO_DENEGADO",
                "El asesor solo puede cancelar pólizas de sus ventas asistidas.",
            ),
        )
    if isinstance(error, ConfirmacionRequerida):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            _error(
                "CONFIRMACION_REQUERIDA",
                "Debes confirmar de forma explícita la cancelación para continuar.",
                campo="confirmo",
            ),
        )
    if isinstance(error, CancelacionNoPermitida):
        principal = error.bloqueos[0]
        return HTTPException(
            status.HTTP_409_CONFLICT,
            _error(
                principal.codigo.value,
                principal.mensaje,
                bloqueos=[b.model_dump(mode="json") for b in error.bloqueos],
            ),
        )
    if isinstance(error, ClaveIdempotenciaReutilizada):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            _error(
                "CLAVE_IDEMPOTENCIA_REUTILIZADA",
                "La clave de la solicitud ya se usó con otra solicitud.",
            ),
        )
    raise error


_ERRORES = (
    PolizaNoEncontrada,
    AccesoDenegado,
    ConfirmacionRequerida,
    CancelacionNoPermitida,
    ClaveIdempotenciaReutilizada,
)


@router.get(
    "/{poliza_id}/cancelacion",
    response_model=CondicionesCancelacion,
    summary="Condiciones para cancelar la póliza: consecuencias, motivos y saldo a favor",
    description=(
        "No guarda nada. Indica si la póliza se puede cancelar hoy y, si no, por qué "
        "(`bloqueos`: póliza no vigente o siniestro en trámite). Si la póliza ya se canceló, "
        "incluye el registro de la cancelación."
    ),
)
def consultar_cancelacion(
    poliza_id: str,
    respuesta: Response,
    solicitante: Solicitante = Depends(solicitante_actual),
    servicio: ServicioCancelaciones = Depends(obtener_servicio),
) -> CondicionesCancelacion:
    respuesta.headers["Cache-Control"] = "no-store"
    try:
        propuesta, cancelacion = servicio.consultar(solicitante, poliza_id)
    except _ERRORES as error:
        raise _traducir(error) from None
    return a_condiciones(propuesta, cancelacion)


@router.post(
    "/{poliza_id}/cancelacion",
    response_model=CancelacionVista,
    status_code=status.HTTP_201_CREATED,
    summary="Cancela la póliza de inmediato",
    description=(
        "Exige `confirmo: true` y un motivo. Recalcula las condiciones en el servidor: si no se "
        "puede cancelar, responde 409 y la póliza queda como estaba. Con el encabezado "
        "Idempotency-Key, repetir la misma solicitud devuelve la misma cancelación (200)."
    ),
    responses={
        200: {"description": "La solicitud ya se había procesado con esa clave."},
        409: {"description": "Póliza no vigente, siniestro en trámite o clave reutilizada."},
        422: {"description": "Falta la confirmación explícita o el motivo no es válido."},
    },
)
def confirmar_cancelacion(
    poliza_id: str,
    solicitud: SolicitudCancelacion,
    respuesta: Response,
    solicitante: Solicitante = Depends(solicitante_actual),
    servicio: ServicioCancelaciones = Depends(obtener_servicio),
    idempotency_key: str | None = Header(default=None, max_length=100),
) -> CancelacionVista:
    respuesta.headers["Cache-Control"] = "no-store"
    try:
        cancelacion, creada = servicio.confirmar(
            solicitante, poliza_id, solicitud, clave_idempotencia=idempotency_key
        )
    except _ERRORES as error:
        raise _traducir(error) from None
    if not creada:
        respuesta.status_code = status.HTTP_200_OK
    return a_cancelacion(cancelacion)
