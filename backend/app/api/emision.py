"""API del documento de la póliza emitida (HU12)."""

import logging
from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.cotizaciones import ActorCotizacion, TipoActorCotizacion, actor_actual
from app.cotizaciones.repositorio import RepositorioCotizacionesPostgres
from app.firmas.repositorio import RepositorioFirmasPostgres
from app.identidad.modelos import Rol
from app.infraestructura.database import SessionLocal, get_db
from app.polizas.almacenamiento import AlmacenDocumentos, AlmacenNoDisponible, crear_almacen
from app.polizas.comunicaciones import ComunicacionesSimuladas
from app.polizas.emision import (
    AccesoDenegado,
    DocumentoAlterado,
    DocumentoDescargable,
    DocumentoNoDisponible,
    ServicioEmision,
)
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.polizas.repositorio_documentos import RepositorioDocumentosPostgres
from app.polizas.servicio import PolizaNoEncontrada

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/polizas", tags=["polizas"])

_almacen = crear_almacen()
_comunicaciones = ComunicacionesSimuladas()


def obtener_almacen() -> AlmacenDocumentos:
    return _almacen


def obtener_comunicaciones() -> ComunicacionesSimuladas:
    return _comunicaciones


def construir_emision(
    db: Session,
    almacen: AlmacenDocumentos | None = None,
    comunicaciones: ComunicacionesSimuladas | None = None,
) -> ServicioEmision:
    comunicaciones = comunicaciones or obtener_comunicaciones()
    return ServicioEmision(
        polizas=RepositorioPolizasPostgres(db),
        documentos=RepositorioDocumentosPostgres(db),
        firmas=RepositorioFirmasPostgres(db),
        cotizaciones=RepositorioCotizacionesPostgres(db),
        almacen=almacen or obtener_almacen(),
        correo=comunicaciones,
        notificador=comunicaciones,
    )


def obtener_emision(
    db: Session = Depends(get_db),
    almacen: AlmacenDocumentos = Depends(obtener_almacen),
    comunicaciones: ComunicacionesSimuladas = Depends(obtener_comunicaciones),
) -> ServicioEmision:
    return construir_emision(db, almacen, comunicaciones)


def obtener_despachador() -> Callable[[str], None]:
    """Función que envía correo y confirmación fuera de la petición.

    Abre su propia sesión de base de datos: la de la petición ya no está disponible cuando la
    tarea en segundo plano se ejecuta.
    """

    def despachar(poliza_id: str) -> None:
        db = SessionLocal()
        try:
            construir_emision(db).notificar(poliza_id)
        except Exception:
            logger.exception("Falló la entrega asíncrona de la póliza %s", poliza_id)
        finally:
            db.close()

    return despachar


_ROLES_CON_ACCESO = {Rol.CLIENTE, Rol.ASESOR_VENTAS}


@router.get(
    "/{poliza_id}/documento",
    response_class=Response,
    summary="Descarga el PDF de la póliza emitida",
    description=(
        "El cliente descarga el documento de su póliza. El asesor de ventas puede descargarlo "
        "solo si participó en la venta asistida. El archivo es el mismo que se emitió: su "
        "huella SHA-256 viaja en el encabezado X-Huella-Documento."
    ),
    responses={
        200: {"content": {"application/pdf": {}}, "description": "Documento PDF."},
        403: {"description": "El asesor no participó en esta venta."},
        404: {"description": "La póliza no existe o no es del cliente."},
        409: {"description": "El documento guardado no coincide con el emitido."},
    },
)
def descargar_documento(
    poliza_id: str,
    actor: ActorCotizacion = Depends(actor_actual),
    servicio: ServicioEmision = Depends(obtener_emision),
) -> Response:
    if actor.tipo is not TipoActorCotizacion.USUARIO or actor.rol not in _ROLES_CON_ACCESO:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "El actor no tiene permiso para consultar pólizas."
        )

    try:
        if actor.rol is Rol.CLIENTE:
            documento = servicio.documento_del_cliente(actor.actor_id, poliza_id)
        else:
            documento = servicio.documento_del_asesor(actor.actor_id, poliza_id)
    except PolizaNoEncontrada:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"codigo": "POLIZA_NO_ENCONTRADA", "mensaje": "La póliza no existe."},
        ) from None
    except AccesoDenegado:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El asesor solo puede consultar pólizas de sus procesos asistidos.",
        ) from None
    except DocumentoNoDisponible:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "codigo": "DOCUMENTO_NO_DISPONIBLE",
                "mensaje": "El documento de la póliza aún no está disponible.",
            },
        ) from None
    except DocumentoAlterado:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "codigo": "DOCUMENTO_ALTERADO",
                "mensaje": "El documento guardado no coincide con el emitido.",
            },
        ) from None
    except AlmacenNoDisponible:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "codigo": "ALMACEN_NO_DISPONIBLE",
                "mensaje": "No se pudo leer el documento. Intente de nuevo en unos minutos.",
            },
        ) from None
    return _respuesta_pdf(documento)


def _respuesta_pdf(documento: DocumentoDescargable) -> Response:
    return Response(
        content=documento.contenido,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{documento.nombre_archivo}"',
            "X-Huella-Documento": documento.huella_sha256,
            "Cache-Control": "no-store",
        },
    )
