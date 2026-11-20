"""API de la asistencia en sitio (HU06).

El cliente autenticado consulta los servicios de asistencia de una póliza vigente suya, crea
una solicitud de asistencia, lista las suyas y cancela una que todavía esté SOLICITADA. El
`cliente_id` sale de la sesión; nunca del cuerpo ni de un query param.

Estas respuestas llevan información personal y contractual: se marcan `Cache-Control: no-store`.
No se registran coordenadas en logs.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.orm import Session

from app.api.seguridad import requiere_roles
from app.asistencias.modelos import NuevaAsistencia
from app.asistencias.repositorio import (
    RepositorioAsistenciasPostgres,
    RepositorioPrestadoresPostgres,
)
from app.asistencias.servicio import (
    AsistenciaAjena,
    AsistenciaNoEncontrada,
    AsistenciaYaCancelada,
    PolizaAjena,
    PolizaNoEncontrada,
    PolizaNoVigente,
    PrestadorNoDisponible,
    PrestadorNoEncontrado,
    ServicioAsistencias,
    ServicioNoDisponible,
    ServicioNoOfrecidoPorPrestador,
)
from app.asistencias.vistas import (
    AsistenciaCreada,
    ServiciosPoliza,
    Ubicacion,
    a_asistencia_creada,
    a_servicios_poliza,
)
from app.identidad.modelos import Rol
from app.infraestructura.database import get_db
from app.polizas.repositorio import RepositorioPolizasPostgres

router = APIRouter(prefix="/api/v1/asistencias", tags=["asistencias"])

cliente_actual = requiere_roles(Rol.CLIENTE)


def obtener_servicio(db: Session = Depends(get_db)) -> ServicioAsistencias:
    return ServicioAsistencias(
        prestadores=RepositorioPrestadoresPostgres(db),
        asistencias=RepositorioAsistenciasPostgres(db),
        polizas=RepositorioPolizasPostgres(db),
    )


def _sin_cache(respuesta: Response) -> None:
    respuesta.headers["Cache-Control"] = "no-store"
    respuesta.headers["Pragma"] = "no-cache"


def traducir_errores_poliza(error: Exception) -> HTTPException:
    """Traduce las excepciones de dominio comunes a HTTP, siguiendo las convenciones del repo."""
    if isinstance(error, PolizaNoEncontrada):
        return HTTPException(
            status.HTTP_404_NOT_FOUND,
            {"codigo": "POLIZA_NO_ENCONTRADA", "mensaje": "La póliza no existe."},
        )
    if isinstance(error, PolizaAjena):
        return HTTPException(
            status.HTTP_403_FORBIDDEN,
            {"codigo": "POLIZA_NO_AUTORIZADA", "mensaje": "No tiene acceso a esta póliza."},
        )
    if isinstance(error, PolizaNoVigente):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            {"codigo": "POLIZA_NO_VIGENTE", "mensaje": "La póliza no está vigente."},
        )
    if isinstance(error, ServicioNoDisponible):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {
                "codigo": "SERVICIO_NO_DISPONIBLE",
                "mensaje": "El ramo de la póliza no ofrece ese servicio de asistencia.",
            },
        )
    if isinstance(error, PrestadorNoEncontrado):
        return HTTPException(
            status.HTTP_404_NOT_FOUND,
            {"codigo": "PRESTADOR_NO_ENCONTRADO", "mensaje": "El prestador no existe."},
        )
    if isinstance(error, PrestadorNoDisponible):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            {"codigo": "PRESTADOR_NO_DISPONIBLE", "mensaje": "El prestador no está disponible."},
        )
    if isinstance(error, ServicioNoOfrecidoPorPrestador):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {
                "codigo": "SERVICIO_NO_OFRECIDO_POR_PRESTADOR",
                "mensaje": "El prestador no ofrece el servicio seleccionado.",
            },
        )
    raise error


@router.get(
    "/servicios",
    response_model=ServiciosPoliza,
    summary="Servicios de asistencia disponibles para una póliza vigente del cliente",
    responses={
        403: {"description": "La póliza no pertenece al cliente autenticado."},
        404: {"description": "La póliza no existe."},
        409: {"description": "La póliza no está vigente."},
    },
)
def servicios_disponibles(
    respuesta: Response,
    poliza_id: str,
    usuario=Depends(cliente_actual),
    servicio: ServicioAsistencias = Depends(obtener_servicio),
) -> ServiciosPoliza:
    _sin_cache(respuesta)
    try:
        poliza = servicio.servicios_de_poliza(str(usuario.id), poliza_id)
    except (PolizaNoEncontrada, PolizaAjena, PolizaNoVigente) as error:
        raise traducir_errores_poliza(error) from None
    # Para VIDA y PARAMETRICO la lista queda vacía: no es un error.
    return a_servicios_poliza(poliza.poliza_id, poliza.ramo)


@router.post(
    "",
    response_model=AsistenciaCreada,
    status_code=status.HTTP_201_CREATED,
    summary="Crea una solicitud de asistencia en sitio sobre una póliza vigente del cliente",
    responses={
        403: {"description": "La póliza no pertenece al cliente autenticado."},
        404: {"description": "La póliza o el prestador no existen."},
        409: {"description": "La póliza no está vigente o el prestador no está disponible."},
        422: {"description": "Servicio incompatible con el ramo o con el prestador."},
    },
)
def crear_asistencia(
    solicitud: NuevaAsistencia,
    respuesta: Response,
    usuario=Depends(cliente_actual),
    servicio: ServicioAsistencias = Depends(obtener_servicio),
) -> AsistenciaCreada:
    _sin_cache(respuesta)
    try:
        asistencia, prestador = servicio.crear(str(usuario.id), solicitud)
    except (
        PolizaNoEncontrada,
        PolizaAjena,
        PolizaNoVigente,
        ServicioNoDisponible,
        PrestadorNoEncontrado,
        PrestadorNoDisponible,
        ServicioNoOfrecidoPorPrestador,
    ) as error:
        raise traducir_errores_poliza(error) from None
    return a_asistencia_creada(asistencia, prestador)


@router.get(
    "",
    response_model=list[AsistenciaCreada],
    summary="Lista las asistencias del cliente autenticado, de la más reciente a la más antigua",
)
def listar_asistencias(
    respuesta: Response,
    usuario=Depends(cliente_actual),
    servicio: ServicioAsistencias = Depends(obtener_servicio),
) -> list[AsistenciaCreada]:
    _sin_cache(respuesta)
    asistencias = servicio.listar_de_cliente(str(usuario.id))
    vistas: list[AsistenciaCreada] = []
    for asistencia in asistencias:
        prestador = servicio._prestadores.obtener(asistencia.prestador_id)
        resumen = (
            prestador if prestador is not None else _prestador_desconocido(asistencia.prestador_id)
        )
        vistas.append(a_asistencia_creada(asistencia, resumen))
    return vistas


@router.post(
    "/{asistencia_id}/cancelacion",
    response_model=AsistenciaCreada,
    summary="Cancela una asistencia SOLICITADA del cliente (no elimina el registro)",
    responses={
        403: {"description": "La asistencia pertenece a otro cliente."},
        404: {"description": "La asistencia no existe."},
        409: {"description": "La asistencia ya estaba cancelada."},
    },
)
def cancelar_asistencia(
    respuesta: Response,
    asistencia_id: str = Path(min_length=1, max_length=50),
    usuario=Depends(cliente_actual),
    servicio: ServicioAsistencias = Depends(obtener_servicio),
) -> AsistenciaCreada:
    _sin_cache(respuesta)
    try:
        asistencia = servicio.cancelar(str(usuario.id), asistencia_id)
    except AsistenciaNoEncontrada:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            {"codigo": "ASISTENCIA_NO_ENCONTRADA", "mensaje": "La asistencia no existe."},
        ) from None
    except AsistenciaAjena:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            {"codigo": "ASISTENCIA_NO_AUTORIZADA", "mensaje": "No tiene acceso a esta asistencia."},
        ) from None
    except AsistenciaYaCancelada:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"codigo": "ASISTENCIA_YA_CANCELADA", "mensaje": "La asistencia ya fue cancelada."},
        ) from None
    prestador = servicio._prestadores.obtener(asistencia.prestador_id)
    resumen = (
        prestador if prestador is not None else _prestador_desconocido(asistencia.prestador_id)
    )
    return a_asistencia_creada(asistencia, resumen)


def _prestador_desconocido(prestador_id: str):
    """Resumen mínimo cuando el prestador ya no está (por ejemplo, retirado del catálogo)."""
    from app.asistencias.modelos import Prestador, TipoServicioAsistencia

    return Prestador(
        prestador_id=prestador_id,
        nombre="Prestador no disponible",
        direccion="—",
        telefono=None,
        latitud=0.0,
        longitud=0.0,
        servicios=[TipoServicioAsistencia.ASISTENCIA_MEDICA],
        activo=False,
    )


__all__ = ["Ubicacion", "obtener_servicio", "router"]
