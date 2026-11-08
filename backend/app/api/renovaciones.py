"""API de renovación de la póliza (HU22 / BPM-35).

Flujo de la app: consultar la propuesta (nueva vigencia, coberturas y prima), iniciar la
renovación (crea la cotización a pagar) y pagarla con `POST /api/v1/pagos`. Cuando el pago se
aprueba, la póliza toma la nueva vigencia; `GET .../renovacion/{id}` informa el resultado.
Renuevan el cliente titular y el asesor de la venta asistida; el pago lo hace el cliente.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.cancelaciones import solicitante_actual
from app.api.enriquecimiento import obtener_consentimientos
from app.api.perfilamiento import obtener_repositorio as obtener_perfiles
from app.cotizaciones.repositorio import RepositorioCotizacionesPostgres
from app.cotizaciones.servicio_personalizacion import ServicioPersonalizacionCotizacion
from app.infraestructura.database import get_db
from app.pagos.repositorio import RepositorioPagosPostgres
from app.perfilamiento.enriquecimiento.puertos import RepositorioConsentimientos
from app.perfilamiento.repositorio import RepositorioPerfiles
from app.polizas.dominio.renovacion import RenovacionNoEncontrada, RenovacionNoPermitida
from app.polizas.emision import AccesoDenegado
from app.polizas.endosos import Solicitante
from app.polizas.renovacion import ServicioRenovaciones
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.polizas.repositorio_renovaciones import RepositorioRenovacionesPostgres
from app.polizas.servicio import PolizaNoEncontrada
from app.polizas.vistas_renovacion import (
    CondicionesRenovacion,
    RenovacionVista,
    a_condiciones,
    a_renovacion,
)

router = APIRouter(prefix="/api/v1/polizas", tags=["renovaciones"])


def obtener_servicio(
    db: Session = Depends(get_db),
    perfiles: RepositorioPerfiles = Depends(obtener_perfiles),
    consentimientos: RepositorioConsentimientos = Depends(obtener_consentimientos),
) -> ServicioRenovaciones:
    return ServicioRenovaciones(
        polizas=RepositorioPolizasPostgres(db),
        renovaciones=RepositorioRenovacionesPostgres(db),
        cotizaciones=RepositorioCotizacionesPostgres(db),
        personalizador=ServicioPersonalizacionCotizacion(
            perfiles=perfiles, consentimientos=consentimientos
        ),
        pagos=RepositorioPagosPostgres(db),
    )


def _error(codigo: str, mensaje: str, **extra: object) -> dict[str, object]:
    return {"codigo": codigo, "mensaje": mensaje, **extra}


def _traducir(error: Exception) -> HTTPException:
    if isinstance(error, PolizaNoEncontrada):
        return HTTPException(
            status.HTTP_404_NOT_FOUND, _error("POLIZA_NO_ENCONTRADA", "La póliza no existe.")
        )
    if isinstance(error, RenovacionNoEncontrada):
        return HTTPException(
            status.HTTP_404_NOT_FOUND,
            _error("RENOVACION_NO_ENCONTRADA", "La renovación no existe."),
        )
    if isinstance(error, AccesoDenegado):
        return HTTPException(
            status.HTTP_403_FORBIDDEN,
            _error(
                "ACCESO_DENEGADO",
                "El asesor solo puede renovar pólizas de sus ventas asistidas.",
            ),
        )
    if isinstance(error, RenovacionNoPermitida):
        principal = error.bloqueos[0]
        return HTTPException(
            status.HTTP_409_CONFLICT,
            _error(
                principal.codigo.value,
                principal.mensaje,
                bloqueos=[b.model_dump(mode="json") for b in error.bloqueos],
            ),
        )
    raise error


_ERRORES = (PolizaNoEncontrada, RenovacionNoEncontrada, AccesoDenegado, RenovacionNoPermitida)


@router.get(
    "/{poliza_id}/renovacion",
    response_model=CondicionesRenovacion,
    summary="Propuesta de renovación: nueva vigencia, coberturas y prima",
    description=(
        "No guarda nada. Indica si la póliza se puede renovar hoy y, si no, por qué "
        "(`bloqueos`). Si hay una renovación en curso esperando el pago, la incluye en "
        "`renovacion`. Antes de responder aplica los pagos aprobados que hayan quedado "
        "pendientes de aplicar."
    ),
)
def consultar_renovacion(
    poliza_id: str,
    respuesta: Response,
    solicitante: Solicitante = Depends(solicitante_actual),
    servicio: ServicioRenovaciones = Depends(obtener_servicio),
) -> CondicionesRenovacion:
    respuesta.headers["Cache-Control"] = "no-store"
    try:
        propuesta, pendiente = servicio.consultar(solicitante, poliza_id)
    except _ERRORES as error:
        raise _traducir(error) from None
    vista = a_renovacion(pendiente, servicio.estado_de(pendiente)) if pendiente else None
    return a_condiciones(propuesta, vista)


@router.post(
    "/{poliza_id}/renovacion",
    response_model=RenovacionVista,
    status_code=status.HTTP_201_CREATED,
    summary="Inicia la renovación: crea la cotización que el cliente debe pagar",
    description=(
        "Recalcula la propuesta en el servidor y crea la cotización de renovación "
        "(`cotizacion_id` y `prima_total` son lo que se paga con `POST /api/v1/pagos`). "
        "La póliza no cambia hasta que el pago se aprueba. Con `Idempotency-Key`, o si ya "
        "hay una renovación vigente esperando el pago, repetir la solicitud devuelve esa "
        "misma renovación (200)."
    ),
    responses={
        200: {"description": "Ya había una renovación vigente esperando el pago."},
        409: {"description": "La póliza no se puede renovar; ver `bloqueos`."},
    },
)
def iniciar_renovacion(
    poliza_id: str,
    respuesta: Response,
    solicitante: Solicitante = Depends(solicitante_actual),
    servicio: ServicioRenovaciones = Depends(obtener_servicio),
    idempotency_key: str | None = Header(default=None, max_length=100),
) -> RenovacionVista:
    respuesta.headers["Cache-Control"] = "no-store"
    try:
        renovacion, creada = servicio.iniciar(solicitante, poliza_id, idempotency_key)
    except _ERRORES as error:
        raise _traducir(error) from None
    if not creada:
        respuesta.status_code = status.HTTP_200_OK
    return a_renovacion(renovacion, servicio.estado_de(renovacion))


@router.get(
    "/{poliza_id}/renovacion/{renovacion_id}",
    response_model=RenovacionVista,
    summary="Estado de una renovación (para saber si el pago ya renovó la póliza)",
    description=(
        "`PENDIENTE_PAGO` mientras espera el pago, `APLICADA` cuando la póliza ya tiene la "
        "nueva vigencia, `VENCIDA` si la cotización venció sin pago y `NO_APLICADA` si se pagó "
        "pero la póliza ya no se podía renovar (`motivo_no_aplicada`)."
    ),
)
def consultar_estado_renovacion(
    poliza_id: str,
    renovacion_id: str,
    respuesta: Response,
    solicitante: Solicitante = Depends(solicitante_actual),
    servicio: ServicioRenovaciones = Depends(obtener_servicio),
) -> RenovacionVista:
    respuesta.headers["Cache-Control"] = "no-store"
    try:
        renovacion = servicio.obtener(solicitante, poliza_id, renovacion_id)
    except _ERRORES as error:
        raise _traducir(error) from None
    return a_renovacion(renovacion, servicio.estado_de(renovacion))
