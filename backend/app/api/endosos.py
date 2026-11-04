"""API de modificación de coberturas y endosos de la póliza (HU16 / BPM-68).

Flujo del portal: consultar las opciones de la póliza, simular el cambio para ver el ajuste
de prima, confirmarlo y descargar el endoso. El cliente opera sobre sus pólizas; el asesor de
ventas, sobre las de ventas que asistió.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import ConfigDict
from sqlalchemy.orm import Session

from app.api.cotizaciones import ActorCotizacion, TipoActorCotizacion, actor_actual
from app.api.emision import obtener_almacen
from app.cotizaciones.repositorio import RepositorioCotizacionesPostgres
from app.infraestructura.database import get_db
from app.polizas.almacenamiento import AlmacenDocumentos, AlmacenNoDisponible
from app.polizas.dominio.endosos import (
    ModificacionInvalida,
    PolizaNoModificable,
    SolicitudModificacion,
)
from app.polizas.dominio.modelos import hoy_en_colombia
from app.polizas.emision import AccesoDenegado, DocumentoAlterado, DocumentoNoDisponible
from app.polizas.endosos import (
    ROLES_QUE_MODIFICAN,
    ClaveIdempotenciaReutilizada,
    EndosoNoEncontrado,
    ServicioEndosos,
    Solicitante,
)
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.polizas.repositorio_endosos import EndosoConcurrente, RepositorioEndososPostgres
from app.polizas.servicio import PolizaNoEncontrada
from app.polizas.vistas_endosos import (
    EndosoVista,
    HistorialEndosos,
    OpcionesModificacion,
    PropuestaVista,
    a_endoso,
    a_opciones,
    a_propuesta,
)

router = APIRouter(prefix="/api/v1/polizas", tags=["endosos"])


class ConfirmacionEndoso(SolicitudModificacion):
    """La solicitud más la aceptación expresa del cliente, que queda en el endoso."""

    model_config = ConfigDict(extra="forbid")

    acepta_condiciones: bool = False


def obtener_servicio(
    db: Session = Depends(get_db),
    almacen: AlmacenDocumentos = Depends(obtener_almacen),
) -> ServicioEndosos:
    return ServicioEndosos(
        polizas=RepositorioPolizasPostgres(db),
        endosos=RepositorioEndososPostgres(db),
        cotizaciones=RepositorioCotizacionesPostgres(db),
        almacen=almacen,
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
            status.HTTP_403_FORBIDDEN, "El actor no tiene permiso para modificar pólizas."
        )
    return Solicitante(
        actor_id=actor.actor_id,
        rol=actor.rol,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


def _error(codigo: str, mensaje: str, campo: str | None = None) -> dict[str, str]:
    detalle = {"codigo": codigo, "mensaje": mensaje}
    if campo:
        detalle["campo"] = campo
    return detalle


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
                "El asesor solo puede modificar pólizas de sus ventas asistidas.",
            ),
        )
    if isinstance(error, ModificacionInvalida):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            _error(error.codigo.value, error.mensaje, error.campo),
        )
    if isinstance(error, PolizaNoModificable):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            _error(
                "POLIZA_NO_MODIFICABLE",
                f"La póliza está {error.estado.value.lower()} y ya no admite cambios.",
            ),
        )
    if isinstance(error, EndosoConcurrente):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            _error(
                "MODIFICACION_CONCURRENTE",
                "La póliza cambió mientras confirmabas. Revisa el detalle y vuelve a intentarlo.",
            ),
        )
    if isinstance(error, ClaveIdempotenciaReutilizada):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            _error(
                "CLAVE_IDEMPOTENCIA_REUTILIZADA",
                "La clave de la solicitud ya se usó con otros cambios.",
            ),
        )
    if isinstance(error, EndosoNoEncontrado | DocumentoNoDisponible):
        return HTTPException(
            status.HTTP_404_NOT_FOUND,
            _error("ENDOSO_NO_ENCONTRADO", "El endoso no existe o su documento no está listo."),
        )
    if isinstance(error, DocumentoAlterado):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            _error("DOCUMENTO_ALTERADO", "El documento guardado no coincide con el emitido."),
        )
    if isinstance(error, AlmacenNoDisponible):
        return HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            _error(
                "ALMACEN_NO_DISPONIBLE",
                "No se pudo guardar o leer el documento. Intenta de nuevo en unos minutos.",
            ),
        )
    raise error


_ERRORES = (
    PolizaNoEncontrada,
    AccesoDenegado,
    ModificacionInvalida,
    PolizaNoModificable,
    EndosoConcurrente,
    ClaveIdempotenciaReutilizada,
    EndosoNoEncontrado,
    DocumentoNoDisponible,
    DocumentoAlterado,
    AlmacenNoDisponible,
)


def _sin_cache(respuesta: Response) -> None:
    respuesta.headers["Cache-Control"] = "no-store"


@router.get(
    "/{poliza_id}/endosos/opciones",
    response_model=OpcionesModificacion,
    summary="Coberturas opcionales, beneficiarios y límites que admite la póliza",
)
def consultar_opciones(
    poliza_id: str,
    respuesta: Response,
    solicitante: Solicitante = Depends(solicitante_actual),
    servicio: ServicioEndosos = Depends(obtener_servicio),
) -> OpcionesModificacion:
    _sin_cache(respuesta)
    try:
        poliza = servicio.poliza(solicitante, poliza_id)
    except _ERRORES as error:
        raise _traducir(error) from None
    return a_opciones(poliza, hoy_en_colombia(datetime.now(UTC)))


@router.post(
    "/{poliza_id}/endosos/simulacion",
    response_model=PropuestaVista,
    summary="Calcula el endoso y el ajuste pro-rata de la prima, sin guardar nada",
)
def simular_endoso(
    poliza_id: str,
    solicitud: SolicitudModificacion,
    respuesta: Response,
    solicitante: Solicitante = Depends(solicitante_actual),
    servicio: ServicioEndosos = Depends(obtener_servicio),
) -> PropuestaVista:
    _sin_cache(respuesta)
    try:
        return a_propuesta(servicio.simular(solicitante, poliza_id, solicitud))
    except _ERRORES as error:
        raise _traducir(error) from None


@router.post(
    "/{poliza_id}/endosos",
    response_model=EndosoVista,
    status_code=status.HTTP_201_CREATED,
    summary="Confirma los cambios y emite el endoso",
    description=(
        "Recalcula el ajuste en el servidor, emite el PDF del endoso y actualiza la póliza. "
        "Con el encabezado Idempotency-Key, repetir la misma solicitud devuelve el mismo endoso "
        "(200) en vez de crear otro."
    ),
    responses={
        200: {"description": "La solicitud ya se había confirmado con esa clave."},
        409: {"description": "Póliza no vigente, cambio concurrente o clave reutilizada."},
        422: {"description": "La solicitud no cumple una regla del endoso."},
    },
)
def confirmar_endoso(
    poliza_id: str,
    confirmacion: ConfirmacionEndoso,
    respuesta: Response,
    solicitante: Solicitante = Depends(solicitante_actual),
    servicio: ServicioEndosos = Depends(obtener_servicio),
    idempotency_key: str | None = Header(default=None, max_length=100),
) -> EndosoVista:
    _sin_cache(respuesta)
    if not confirmacion.acepta_condiciones:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            _error(
                "CONFIRMACION_REQUERIDA",
                "Debes aceptar los cambios y el ajuste de prima para emitir el endoso.",
                "acepta_condiciones",
            ),
        )
    solicitud = SolicitudModificacion(
        beneficiarios=confirmacion.beneficiarios,
        coberturas_opcionales=confirmacion.coberturas_opcionales,
    )
    try:
        endoso, creado = servicio.confirmar(solicitante, poliza_id, solicitud, idempotency_key)
    except _ERRORES as error:
        raise _traducir(error) from None
    if not creado:
        respuesta.status_code = status.HTTP_200_OK
    return a_endoso(endoso)


@router.get(
    "/{poliza_id}/endosos",
    response_model=HistorialEndosos,
    summary="Endosos de la póliza, del más antiguo al más reciente",
)
def listar_endosos(
    poliza_id: str,
    respuesta: Response,
    solicitante: Solicitante = Depends(solicitante_actual),
    servicio: ServicioEndosos = Depends(obtener_servicio),
) -> HistorialEndosos:
    _sin_cache(respuesta)
    try:
        endosos = servicio.listar(solicitante, poliza_id)
    except _ERRORES as error:
        raise _traducir(error) from None
    return HistorialEndosos(endosos=[a_endoso(e) for e in endosos])


@router.get(
    "/{poliza_id}/endosos/{endoso_id}/documento",
    response_class=Response,
    summary="Descarga el PDF del endoso",
    responses={200: {"content": {"application/pdf": {}}, "description": "Documento PDF."}},
)
def descargar_endoso(
    poliza_id: str,
    endoso_id: str,
    solicitante: Solicitante = Depends(solicitante_actual),
    servicio: ServicioEndosos = Depends(obtener_servicio),
) -> Response:
    try:
        documento = servicio.documento(solicitante, poliza_id, endoso_id)
    except _ERRORES as error:
        raise _traducir(error) from None
    return Response(
        content=documento.contenido,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{documento.nombre_archivo}"',
            "X-Huella-Documento": documento.huella_sha256,
            "Cache-Control": "no-store",
        },
    )
