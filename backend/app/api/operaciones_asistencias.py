"""API de seguimiento operativo de la asistencia en sitio (HU06 ampliación).

El rol OPERACIONES_SINIESTROS consulta las solicitudes de asistencia, ve su detalle, las acepta
(pasando SOLICITADA -> ACEPTADA, con tiempo estimado de llegada opcional) y actualiza ese ETA
después. El cliente no tiene acceso a estos endpoints; estos endpoints no exponen datos
personales del cliente más allá de su identificador.

Reutiliza el `ServicioAsistencias` y su dependencia `obtener_servicio` del módulo del cliente.
Respuestas con `Cache-Control: no-store`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.api.asistencias import obtener_servicio
from app.api.seguridad import requiere_roles
from app.asistencias.modelos import (
    AceptacionAsistencia,
    EstadoAsistencia,
    SeguimientoAsistencia,
    TipoServicioAsistencia,
)
from app.asistencias.servicio import (
    AsistenciaCancelada,
    AsistenciaNoEncontrada,
    AsistenciaYaAceptada,
    ServicioAsistencias,
    TransicionEstadoInvalida,
)
from app.asistencias.vistas import AsistenciaOperaciones, a_asistencia_operaciones
from app.identidad.modelos import Rol
from app.infraestructura.database import get_db
from app.polizas.repositorio import RepositorioPolizasPostgres

router = APIRouter(prefix="/api/v1/operaciones/asistencias", tags=["operaciones-asistencias"])

operaciones_actual = requiere_roles(Rol.OPERACIONES_SINIESTROS)


def obtener_polizas(db: Session = Depends(get_db)) -> RepositorioPolizasPostgres:
    return RepositorioPolizasPostgres(db)


def _sin_cache(respuesta: Response) -> None:
    respuesta.headers["Cache-Control"] = "no-store"
    respuesta.headers["Pragma"] = "no-cache"


def _a_vista(
    servicio: ServicioAsistencias, polizas: RepositorioPolizasPostgres, asistencia
) -> AsistenciaOperaciones:
    prestador = servicio._prestadores.obtener(asistencia.prestador_id)
    if prestador is None:
        from app.api.asistencias import _prestador_desconocido

        prestador = _prestador_desconocido(asistencia.prestador_id)
    poliza = polizas.obtener(asistencia.poliza_id)
    numero_poliza = poliza.numero_poliza if poliza is not None else None
    return a_asistencia_operaciones(asistencia, prestador, numero_poliza)


@router.get(
    "",
    response_model=list[AsistenciaOperaciones],
    summary="Lista las solicitudes de asistencia para seguimiento operativo (filtros opcionales)",
)
def listar_asistencias_operaciones(
    respuesta: Response,
    estado: Annotated[EstadoAsistencia | None, Query()] = None,
    poliza_id: Annotated[str | None, Query(max_length=50)] = None,
    prestador_id: Annotated[str | None, Query(max_length=50)] = None,
    _usuario=Depends(operaciones_actual),
    servicio: ServicioAsistencias = Depends(obtener_servicio),
    polizas: RepositorioPolizasPostgres = Depends(obtener_polizas),
) -> list[AsistenciaOperaciones]:
    _sin_cache(respuesta)
    asistencias = servicio.listar_para_operaciones(
        estado=estado, poliza_id=poliza_id, prestador_id=prestador_id
    )
    return [_a_vista(servicio, polizas, a) for a in asistencias]


@router.get(
    "/{asistencia_id}",
    response_model=AsistenciaOperaciones,
    summary="Detalle de una solicitud de asistencia para seguimiento operativo",
    responses={404: {"description": "La asistencia no existe."}},
)
def detalle_asistencia_operaciones(
    respuesta: Response,
    asistencia_id: str = Path(min_length=1, max_length=50),
    _usuario=Depends(operaciones_actual),
    servicio: ServicioAsistencias = Depends(obtener_servicio),
    polizas: RepositorioPolizasPostgres = Depends(obtener_polizas),
) -> AsistenciaOperaciones:
    _sin_cache(respuesta)
    try:
        asistencia = servicio.obtener_para_operaciones(asistencia_id)
    except AsistenciaNoEncontrada:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            {"codigo": "ASISTENCIA_NO_ENCONTRADA", "mensaje": "La asistencia no existe."},
        ) from None
    return _a_vista(servicio, polizas, asistencia)


@router.post(
    "/{asistencia_id}/aceptacion",
    response_model=AsistenciaOperaciones,
    summary="Operaciones acepta una asistencia SOLICITADA (ETA opcional)",
    responses={
        404: {"description": "La asistencia no existe."},
        409: {"description": "La asistencia ya fue aceptada o está cancelada."},
    },
)
def aceptar_asistencia(
    solicitud: AceptacionAsistencia,
    respuesta: Response,
    asistencia_id: str = Path(min_length=1, max_length=50),
    _usuario=Depends(operaciones_actual),
    servicio: ServicioAsistencias = Depends(obtener_servicio),
    polizas: RepositorioPolizasPostgres = Depends(obtener_polizas),
) -> AsistenciaOperaciones:
    _sin_cache(respuesta)
    try:
        asistencia = servicio.aceptar(asistencia_id, solicitud)
    except AsistenciaNoEncontrada:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            {"codigo": "ASISTENCIA_NO_ENCONTRADA", "mensaje": "La asistencia no existe."},
        ) from None
    except AsistenciaYaAceptada:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"codigo": "ASISTENCIA_YA_ACEPTADA", "mensaje": "La asistencia ya fue aceptada."},
        ) from None
    except AsistenciaCancelada:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"codigo": "ASISTENCIA_CANCELADA", "mensaje": "La asistencia está cancelada."},
        ) from None
    return _a_vista(servicio, polizas, asistencia)


@router.patch(
    "/{asistencia_id}/seguimiento",
    response_model=AsistenciaOperaciones,
    summary="Operaciones actualiza el tiempo estimado de llegada de una asistencia ACEPTADA",
    responses={
        404: {"description": "La asistencia no existe."},
        409: {"description": "La asistencia no está ACEPTADA; el ETA no aplica."},
    },
)
def actualizar_seguimiento(
    solicitud: SeguimientoAsistencia,
    respuesta: Response,
    asistencia_id: str = Path(min_length=1, max_length=50),
    _usuario=Depends(operaciones_actual),
    servicio: ServicioAsistencias = Depends(obtener_servicio),
    polizas: RepositorioPolizasPostgres = Depends(obtener_polizas),
) -> AsistenciaOperaciones:
    _sin_cache(respuesta)
    try:
        asistencia = servicio.actualizar_seguimiento(asistencia_id, solicitud)
    except AsistenciaNoEncontrada:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            {"codigo": "ASISTENCIA_NO_ENCONTRADA", "mensaje": "La asistencia no existe."},
        ) from None
    except TransicionEstadoInvalida:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {
                "codigo": "TRANSICION_ESTADO_INVALIDA",
                "mensaje": "Solo se puede registrar el ETA de una asistencia aceptada.",
            },
        ) from None
    return _a_vista(servicio, polizas, asistencia)


__all__ = ["TipoServicioAsistencia", "router"]
