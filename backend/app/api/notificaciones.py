"""API de las notificaciones del cliente (HU05): bandeja, dispositivos push y preferencia.

La app móvil consulta aquí sus notificaciones (también las que llegaron con el push apagado),
registra el token de FCM de su teléfono al iniciar sesión, lo da de baja al cerrarla y decide si
quiere recibir push. Solo opera sobre lo del cliente autenticado.
"""

import os
import secrets
from datetime import date, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.cotizaciones import ActorCotizacion, TipoActorCotizacion, actor_actual
from app.identidad.modelos import Rol
from app.infraestructura.database import get_db
from app.notificaciones.bandeja import NotificacionNoEncontrada, ServicioBandeja
from app.notificaciones.composicion import crear_servicio_notificaciones
from app.notificaciones.modelos import Notificacion, TipoNotificacion
from app.notificaciones.repositorio import (
    RepositorioDispositivosPostgres,
    RepositorioNotificacionesPostgres,
    RepositorioPreferenciasPostgres,
)
from app.notificaciones.vencimientos import ResumenVencimientos, ServicioVencimientos
from app.polizas.repositorio import RepositorioPolizasPostgres

router = APIRouter(prefix="/api/v1/notificaciones", tags=["notificaciones"])


def obtener_servicio(db: Session = Depends(get_db)) -> ServicioBandeja:
    return ServicioBandeja(
        notificaciones=RepositorioNotificacionesPostgres(db),
        dispositivos=RepositorioDispositivosPostgres(db),
        preferencias=RepositorioPreferenciasPostgres(db),
    )


def cliente_actual(actor: ActorCotizacion = Depends(actor_actual)) -> str:
    if actor.tipo is not TipoActorCotizacion.USUARIO or actor.rol is not Rol.CLIENTE:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo el cliente asegurado puede consultar sus notificaciones.",
        )
    return actor.actor_id


# --- Vistas --------------------------------------------------------------------------------


class NotificacionVista(BaseModel):
    """Una notificación como la ve el cliente: sin su identificador ni datos internos."""

    model_config = ConfigDict(frozen=True)

    notificacion_id: str
    tipo: TipoNotificacion
    titulo: str
    cuerpo: str
    # A dónde lleva al tocarla (poliza_id, siniestro_id…) y datos para mostrarla.
    datos: dict[str, str]
    creada_en: datetime
    leida: bool
    leida_en: datetime | None


def a_vista(notificacion: Notificacion) -> NotificacionVista:
    return NotificacionVista(
        notificacion_id=notificacion.notificacion_id,
        tipo=notificacion.tipo,
        titulo=notificacion.titulo,
        cuerpo=notificacion.cuerpo,
        datos=notificacion.datos,
        creada_en=notificacion.creada_en,
        leida=notificacion.leida,
        leida_en=notificacion.leida_en,
    )


class ListaNotificaciones(BaseModel):
    notificaciones: list[NotificacionVista]
    no_leidas: int


class ConteoNoLeidas(BaseModel):
    no_leidas: int


class LecturaNotificacion(BaseModel):
    notificacion_id: str
    leida: bool
    no_leidas: int


class SolicitudDispositivo(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # Token de FCM del teléfono. No se devuelve ni se registra en los errores.
    token: str = Field(min_length=1, max_length=512)
    plataforma: str = Field(default="ANDROID", pattern=r"^[A-Z]{3,20}$")


class BajaDispositivo(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    token: str = Field(min_length=1, max_length=512)


class PreferenciaPush(BaseModel):
    model_config = ConfigDict(extra="forbid")

    push_habilitado: bool


def _sin_cache(respuesta: Response) -> None:
    respuesta.headers["Cache-Control"] = "no-store"


# --- Bandeja -------------------------------------------------------------------------------


@router.get(
    "",
    response_model=ListaNotificaciones,
    summary="Lista las notificaciones del cliente, la más reciente primero",
    description=(
        "Incluye todos los eventos registrados, también los que llegaron con el push "
        "deshabilitado. `no_leidas` cuenta todas, no solo las de la página."
    ),
)
def listar(
    respuesta: Response,
    limite: int = Query(default=50, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    cliente_id: str = Depends(cliente_actual),
    servicio: ServicioBandeja = Depends(obtener_servicio),
) -> ListaNotificaciones:
    _sin_cache(respuesta)
    notificaciones, no_leidas = servicio.listar(cliente_id, limite, desplazamiento)
    return ListaNotificaciones(
        notificaciones=[a_vista(n) for n in notificaciones], no_leidas=no_leidas
    )


@router.get(
    "/no-leidas",
    response_model=ConteoNoLeidas,
    summary="Cuántas notificaciones no ha leído el cliente (para la insignia de la campana)",
)
def contar_no_leidas(
    respuesta: Response,
    cliente_id: str = Depends(cliente_actual),
    servicio: ServicioBandeja = Depends(obtener_servicio),
) -> ConteoNoLeidas:
    _sin_cache(respuesta)
    return ConteoNoLeidas(no_leidas=servicio.contar_no_leidas(cliente_id))


# Las rutas fijas van antes que las de `{notificacion_id}` para que no se confundan.


@router.get(
    "/preferencias",
    response_model=PreferenciaPush,
    summary="Si el cliente quiere recibir push (por defecto sí)",
)
def obtener_preferencia(
    respuesta: Response,
    cliente_id: str = Depends(cliente_actual),
    servicio: ServicioBandeja = Depends(obtener_servicio),
) -> PreferenciaPush:
    _sin_cache(respuesta)
    return PreferenciaPush(push_habilitado=servicio.push_habilitado(cliente_id))


@router.put(
    "/preferencias",
    response_model=PreferenciaPush,
    summary="Habilita o deshabilita el push",
    description=(
        "Con el push deshabilitado los eventos siguen registrándose en la bandeja; solo deja "
        "de enviarse el aviso al teléfono."
    ),
)
def cambiar_preferencia(
    solicitud: PreferenciaPush,
    respuesta: Response,
    cliente_id: str = Depends(cliente_actual),
    servicio: ServicioBandeja = Depends(obtener_servicio),
) -> PreferenciaPush:
    _sin_cache(respuesta)
    return PreferenciaPush(
        push_habilitado=servicio.cambiar_preferencia(cliente_id, solicitud.push_habilitado)
    )


@router.put(
    "/dispositivos",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Registra el token de FCM del teléfono",
    description=(
        "La app lo llama al iniciar sesión y cada vez que FCM le da un token nuevo. Repetirlo no "
        "duplica el dispositivo. Si el teléfono lo usaba otro cliente, pasa a quien lo registra."
    ),
)
def registrar_dispositivo(
    solicitud: SolicitudDispositivo,
    cliente_id: str = Depends(cliente_actual),
    servicio: ServicioBandeja = Depends(obtener_servicio),
) -> Response:
    servicio.registrar_dispositivo(cliente_id, solicitud.token, solicitud.plataforma)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/dispositivos/baja",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Da de baja el token del teléfono (cierre de sesión)",
    description=(
        "Es tolerante: responde 204 aunque el token no exista o sea de otro cliente, sin "
        "revelarlo. Va por POST con el token en el cuerpo para que no quede en las URL."
    ),
)
def dar_de_baja_dispositivo(
    solicitud: BajaDispositivo,
    cliente_id: str = Depends(cliente_actual),
    servicio: ServicioBandeja = Depends(obtener_servicio),
) -> Response:
    servicio.dar_de_baja_dispositivo(cliente_id, solicitud.token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{notificacion_id}/leida",
    response_model=LecturaNotificacion,
    summary="Marca una notificación como leída",
    description="Repetirlo no cambia nada. 404 si no existe o es de otro cliente.",
    responses={404: {"description": "La notificación no existe."}},
)
def marcar_leida(
    notificacion_id: str,
    respuesta: Response,
    cliente_id: str = Depends(cliente_actual),
    servicio: ServicioBandeja = Depends(obtener_servicio),
) -> LecturaNotificacion:
    _sin_cache(respuesta)
    try:
        no_leidas = servicio.marcar_leida(cliente_id, notificacion_id)
    except NotificacionNoEncontrada:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "codigo": "NOTIFICACION_NO_ENCONTRADA",
                "mensaje": "La notificación no existe.",
            },
        ) from None
    return LecturaNotificacion(notificacion_id=notificacion_id, leida=True, no_leidas=no_leidas)


# --- Job interno de vencimientos -----------------------------------------------------------

router_interno = APIRouter(
    prefix="/api/v1/internos/notificaciones", tags=["notificaciones-internas"]
)


def verificar_clave_interna(x_clave_interna: str | None = Header(default=None)) -> None:
    """El job lo llama un proceso programado, no un usuario: se autentica con una clave.

    Sin `NOTIFICACIONES_CLAVE_INTERNA` configurada el endpoint está apagado: no hay una clave
    por defecto que pueda quedar activa por olvido en un despliegue.
    """
    esperada = os.getenv("NOTIFICACIONES_CLAVE_INTERNA")
    if not esperada:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "codigo": "JOB_NO_CONFIGURADO",
                "mensaje": "El job de notificaciones no está configurado.",
            },
        )
    if not x_clave_interna or not secrets.compare_digest(
        x_clave_interna.encode(), esperada.encode()
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"codigo": "CLAVE_INVALIDA", "mensaje": "Clave interna ausente o inválida."},
        )


def obtener_vencimientos(db: Session = Depends(get_db)) -> ServicioVencimientos:
    return ServicioVencimientos(
        polizas=RepositorioPolizasPostgres(db),
        notificaciones=crear_servicio_notificaciones(db),
    )


@router_interno.post(
    "/vencimientos",
    response_model=ResumenVencimientos,
    dependencies=[Depends(verificar_clave_interna)],
    summary="Avisa las pólizas que vencen en 15 y en 3 días",
    description=(
        "Lo llama un proceso programado una vez al día (header `X-Clave-Interna`). Es idempotente: "
        "repetirlo el mismo día no duplica avisos. `fecha` (opcional) corre el job como si fuera "
        "ese día, para recuperar una ejecución perdida o para probar."
    ),
    responses={
        401: {"description": "Clave interna inválida."},
        503: {"description": "El job no está configurado."},
    },
)
def ejecutar_vencimientos(
    respuesta: Response,
    fecha: date | None = None,
    servicio: ServicioVencimientos = Depends(obtener_vencimientos),
) -> ResumenVencimientos:
    _sin_cache(respuesta)
    return servicio.ejecutar(fecha)
