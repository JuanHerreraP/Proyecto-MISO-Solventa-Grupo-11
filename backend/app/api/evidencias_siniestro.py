"""API de evidencias del siniestro (HU04) con integridad y auditoría (EC10).

- El CLIENTE adjunta fotos o videos a sus siniestros abiertos y los consulta.
- OPERACIONES_SINIESTROS y ANALISTA_CUMPLIMIENTO consultan y descargan las evidencias de
  cualquier siniestro y su bitácora de auditoría.
- No hay endpoints para modificar ni borrar: las evidencias son inmutables.
"""

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.seguridad import get_current_user
from app.infraestructura.database import get_db
from app.polizas.almacenamiento import AlmacenDocumentos, AlmacenNoDisponible
from app.siniestros.evidencias import (
    FORMATOS,
    LIMITE_LECTURA_BYTES,
    AccesoDenegado,
    AccesoEvidencia,
    Actor,
    ArchivoDemasiadoGrande,
    ArchivoVacio,
    ContenidoNoCoincide,
    DatosCaptura,
    ErrorEvidencia,
    EvidenciaAlterada,
    EvidenciaNoEncontrada,
    EvidenciaSiniestro,
    FechaCapturaInvalida,
    HuellaNoCoincide,
    LimiteEvidencias,
    ServicioEvidencias,
    SiniestroCerrado,
    SiniestroNoEncontrado,
    TipoNoPermitido,
    crear_almacen_evidencias,
)
from app.siniestros.repositorio import RepositorioSiniestrosPostgres
from app.siniestros.repositorio_evidencias import (
    RepositorioAuditoriaEvidenciasPostgres,
    RepositorioEvidenciasPostgres,
)

router = APIRouter(prefix="/api/v1/siniestros", tags=["evidencias de siniestro"])

_almacen: AlmacenDocumentos | None = None

ESTADOS_HTTP: dict[type[ErrorEvidencia], int] = {
    SiniestroNoEncontrado: status.HTTP_404_NOT_FOUND,
    EvidenciaNoEncontrada: status.HTTP_404_NOT_FOUND,
    AccesoDenegado: status.HTTP_403_FORBIDDEN,
    SiniestroCerrado: status.HTTP_409_CONFLICT,
    LimiteEvidencias: status.HTTP_409_CONFLICT,
    EvidenciaAlterada: status.HTTP_409_CONFLICT,
    TipoNoPermitido: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    ArchivoDemasiadoGrande: status.HTTP_413_CONTENT_TOO_LARGE,
    ArchivoVacio: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ContenidoNoCoincide: status.HTTP_422_UNPROCESSABLE_CONTENT,
    HuellaNoCoincide: status.HTTP_422_UNPROCESSABLE_CONTENT,
    FechaCapturaInvalida: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def obtener_almacen() -> AlmacenDocumentos:
    """Un solo almacén por proceso: conserva la pausa tras un fallo de S3."""
    global _almacen
    if _almacen is None:
        _almacen = crear_almacen_evidencias()
    return _almacen


def obtener_servicio(
    db: Session = Depends(get_db),
    almacen: AlmacenDocumentos = Depends(obtener_almacen),
) -> ServicioEvidencias:
    return ServicioEvidencias(
        siniestros=RepositorioSiniestrosPostgres(db),
        evidencias=RepositorioEvidenciasPostgres(db),
        auditoria=RepositorioAuditoriaEvidenciasPostgres(db),
        almacen=almacen,
    )


def _actor(usuario, request: Request) -> Actor:
    return Actor(
        id=str(usuario.id),
        rol=usuario.rol,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


def _ejecutar(accion):
    """Ejecuta un caso de uso y traduce sus errores a HTTP con un código estable."""
    try:
        return accion()
    except ErrorEvidencia as error:
        codigo_http = ESTADOS_HTTP.get(type(error), status.HTTP_422_UNPROCESSABLE_CONTENT)
        raise HTTPException(
            codigo_http, detail={"codigo": error.codigo, "mensaje": error.mensaje}
        ) from None
    except AlmacenNoDisponible:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "codigo": "ALMACEN_NO_DISPONIBLE",
                "mensaje": "No pudimos guardar o leer la evidencia. Inténtalo de nuevo.",
            },
        ) from None


@router.post(
    "/{siniestro_id}/evidencias",
    response_model=EvidenciaSiniestro,
    status_code=status.HTTP_201_CREATED,
    summary="Adjunta una foto o un video a un siniestro abierto del cliente",
    description=(
        "Multipart con `archivo` y, opcionalmente, `capturada_en` (ISO 8601 con zona), "
        "`latitud`, `longitud` y `precision_metros`. Con el encabezado `X-Contenido-SHA256` el "
        "servidor verifica que el archivo llegó íntegro. Reenviar el mismo archivo devuelve la "
        "evidencia ya registrada (200)."
    ),
    responses={
        200: {"description": "El mismo archivo ya estaba adjunto al siniestro."},
        403: {"description": "Solo el cliente titular adjunta evidencias."},
        404: {"description": "El siniestro no existe o no es del cliente."},
        409: {"description": "El siniestro ya fue evaluado o llegó al máximo de evidencias."},
        413: {"description": "La foto supera 10 MB o el video 50 MB."},
        415: {"description": "Tipo de archivo no admitido."},
        422: {"description": "Archivo vacío, contenido que no corresponde o huella distinta."},
        503: {"description": "El almacén de evidencias no está disponible."},
    },
)
def adjuntar_evidencia(
    siniestro_id: str,
    request: Request,
    respuesta: Response,
    archivo: UploadFile = File(...),
    capturada_en: str | None = Form(default=None),
    latitud: float | None = Form(default=None),
    longitud: float | None = Form(default=None),
    precision_metros: float | None = Form(default=None),
    huella_declarada: str | None = Header(
        default=None, alias="X-Contenido-SHA256", pattern=r"^[0-9a-fA-F]{64}$"
    ),
    usuario=Depends(get_current_user),
    servicio: ServicioEvidencias = Depends(obtener_servicio),
) -> EvidenciaSiniestro:
    try:
        datos = DatosCaptura(
            capturada_en=capturada_en or None,
            latitud=latitud,
            longitud=longitud,
            precision_metros=precision_metros,
            nombre_archivo=archivo.filename,
        )
    except ValidationError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "codigo": "DATOS_CAPTURA_INVALIDOS",
                "mensaje": (
                    "Revisa la fecha de captura (ISO 8601 con zona) y la ubicación "
                    "(latitud y longitud juntas y dentro de rango)."
                ),
            },
        ) from None

    # Se lee como máximo un byte más que el límite mayor: un archivo enorme no llena la memoria.
    contenido = archivo.file.read(LIMITE_LECTURA_BYTES + 1)
    resultado = _ejecutar(
        lambda: servicio.adjuntar(
            actor=_actor(usuario, request),
            siniestro_id=siniestro_id,
            contenido=contenido,
            tipo_contenido=archivo.content_type,
            datos=datos,
            huella_declarada=huella_declarada,
        )
    )
    if not resultado.creada:
        respuesta.status_code = status.HTTP_200_OK
    return resultado.evidencia


@router.get(
    "/{siniestro_id}/evidencias",
    response_model=list[EvidenciaSiniestro],
    summary="Lista las evidencias de un siniestro (titular, Operaciones o Cumplimiento)",
)
def listar_evidencias(
    siniestro_id: str,
    request: Request,
    respuesta: Response,
    usuario=Depends(get_current_user),
    servicio: ServicioEvidencias = Depends(obtener_servicio),
) -> list[EvidenciaSiniestro]:
    respuesta.headers["Cache-Control"] = "no-store"
    return _ejecutar(lambda: servicio.listar(_actor(usuario, request), siniestro_id))


@router.get(
    "/{siniestro_id}/evidencias/auditoria",
    response_model=list[AccesoEvidencia],
    summary="Bitácora de auditoría de las evidencias (Operaciones o Cumplimiento)",
)
def auditoria_evidencias(
    siniestro_id: str,
    request: Request,
    respuesta: Response,
    usuario=Depends(get_current_user),
    servicio: ServicioEvidencias = Depends(obtener_servicio),
) -> list[AccesoEvidencia]:
    respuesta.headers["Cache-Control"] = "no-store"
    return _ejecutar(lambda: servicio.auditoria(_actor(usuario, request), siniestro_id))


@router.get(
    "/{siniestro_id}/evidencias/{evidencia_id}/contenido",
    summary="Descarga el archivo de una evidencia después de verificar su huella",
    responses={
        200: {"description": "El archivo, con su huella en `X-Huella-Evidencia`."},
        409: {"description": "El archivo almacenado no coincide con la huella registrada."},
    },
)
def descargar_evidencia(
    siniestro_id: str,
    evidencia_id: str,
    request: Request,
    usuario=Depends(get_current_user),
    servicio: ServicioEvidencias = Depends(obtener_servicio),
) -> Response:
    evidencia, contenido = _ejecutar(
        lambda: servicio.leer(_actor(usuario, request), siniestro_id, evidencia_id)
    )
    extension = FORMATOS[evidencia.tipo_contenido].extension
    return Response(
        content=contenido,
        media_type=evidencia.tipo_contenido,
        headers={
            "Content-Disposition": f'attachment; filename="{evidencia.evidencia_id}.{extension}"',
            "X-Huella-Evidencia": evidencia.huella_sha256,
            "Cache-Control": "no-store",
        },
    )
