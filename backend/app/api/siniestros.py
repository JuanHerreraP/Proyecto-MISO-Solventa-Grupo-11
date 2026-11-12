"""API del registro manual de siniestros (HU20, HU04).

El router autentica, valida el rol, delega en el servicio y traduce las excepciones de
dominio a códigos HTTP.

- El CLIENTE registra y consulta siniestros sobre sus propias pólizas; el `cliente_id`
  sale de su sesión y nunca del cuerpo.
- El ASESOR_VENTAS registra y consulta siniestros en nombre de un cliente que atiende.
  Debe indicar `cliente_id` y estar asociado a ese cliente (tabla asesor_cliente).
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.seguridad import get_current_user
from app.identidad.asociacion import RepositorioAsesorClientePostgres
from app.identidad.modelos import Rol
from app.infraestructura.database import get_db
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.siniestros.modelos import Siniestro, SolicitudSiniestro, SolicitudSiniestroAsesor
from app.siniestros.repositorio import RepositorioSiniestrosPostgres
from app.siniestros.servicio import (
    ClaveIdempotenciaReutilizada,
    FechaEventoInvalida,
    PolizaAjena,
    PolizaNoEncontrada,
    PolizaNoVigente,
    ServicioSiniestros,
)

router = APIRouter(prefix="/api/v1/siniestros", tags=["siniestros"])

CLIENTE_NO_ASOCIADO = {
    "codigo": "CLIENTE_NO_ASOCIADO",
    "mensaje": "El cliente no está asociado a tu cuenta de asesor.",
}


def obtener_servicio(db: Session = Depends(get_db)) -> ServicioSiniestros:
    return ServicioSiniestros(
        siniestros=RepositorioSiniestrosPostgres(db),
        polizas=RepositorioPolizasPostgres(db),
    )


def obtener_asociaciones(db: Session = Depends(get_db)) -> RepositorioAsesorClientePostgres:
    return RepositorioAsesorClientePostgres(db)


def _traducir_errores_registro(accion):
    """Ejecuta un registro y traduce las excepciones de dominio a HTTP."""
    try:
        return accion()
    except PolizaNoEncontrada:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"codigo": "POLIZA_NO_ENCONTRADA", "mensaje": "La póliza no existe."},
        ) from None
    except PolizaAjena:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"codigo": "POLIZA_AJENA", "mensaje": "No tiene acceso a esta póliza."},
        ) from None
    except PolizaNoVigente:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={"codigo": "POLIZA_NO_VIGENTE", "mensaje": "La póliza no está vigente."},
        ) from None
    except FechaEventoInvalida as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"codigo": error.codigo, "mensaje": error.mensaje},
        ) from None
    except ClaveIdempotenciaReutilizada:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "codigo": "IDEMPOTENCY_KEY_REUTILIZADA",
                "mensaje": "La Idempotency-Key ya se usó con un siniestro distinto.",
            },
        ) from None


@router.post(
    "",
    response_model=Siniestro,
    status_code=status.HTTP_201_CREATED,
    summary="Registra manualmente un siniestro sobre una póliza vigente del cliente",
    description=(
        "Con el encabezado Idempotency-Key, repetir la misma solicitud devuelve el siniestro ya "
        "registrado (200) en lugar de crear otro: la app lo usa al reenviar un borrador (HU04)."
    ),
    responses={
        200: {"description": "Repetición con la misma Idempotency-Key: el siniestro ya existía."},
        403: {"description": "La póliza no pertenece al cliente autenticado."},
        404: {"description": "La póliza no existe."},
        409: {
            "description": (
                "La póliza no está vigente, o la Idempotency-Key ya se usó con otros datos."
            )
        },
        422: {"description": "La fecha del evento es futura o está fuera de la vigencia."},
    },
)
def registrar_siniestro(
    solicitud: SolicitudSiniestro,
    respuesta: Response,
    usuario=Depends(get_current_user),
    servicio: ServicioSiniestros = Depends(obtener_servicio),
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", min_length=8, max_length=80
    ),
) -> Siniestro:
    # El cliente asegurado registra sobre sus propias pólizas.
    if usuario.rol != Rol.CLIENTE.value:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "codigo": "ACCESS_DENIED",
                "mensaje": "Solo el cliente asegurado puede registrar su siniestro.",
            },
        )

    cliente_id = str(usuario.id)
    registro = _traducir_errores_registro(
        lambda: servicio.registrar(
            cliente_id=cliente_id,
            registrado_por=cliente_id,
            solicitud=solicitud,
            clave_idempotencia=idempotency_key,
        )
    )
    if not registro.creado:
        respuesta.status_code = status.HTTP_200_OK
    return registro.siniestro


@router.post(
    "/asistido",
    response_model=Siniestro,
    status_code=status.HTTP_201_CREATED,
    summary="Un asesor registra un siniestro en nombre de un cliente que atiende",
    responses={
        403: {"description": "El cliente no está asociado al asesor o la póliza es ajena."},
        404: {"description": "La póliza no existe."},
        409: {"description": "La póliza no está vigente."},
        422: {"description": "La fecha del evento es futura o está fuera de la vigencia."},
    },
)
def registrar_siniestro_asistido(
    solicitud: SolicitudSiniestroAsesor,
    usuario=Depends(get_current_user),
    servicio: ServicioSiniestros = Depends(obtener_servicio),
    asociaciones: RepositorioAsesorClientePostgres = Depends(obtener_asociaciones),
) -> Siniestro:
    if usuario.rol != Rol.ASESOR_VENTAS.value:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "codigo": "ACCESS_DENIED",
                "mensaje": "Solo un asesor de ventas puede registrar un siniestro asistido.",
            },
        )

    asesor_id = str(usuario.id)
    if not asociaciones.existe_asociacion(asesor_id, solicitud.cliente_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=CLIENTE_NO_ASOCIADO)

    datos = SolicitudSiniestro(
        poliza_id=solicitud.poliza_id,
        tipo_siniestro=solicitud.tipo_siniestro,
        fecha_evento=solicitud.fecha_evento,
        hora_evento=solicitud.hora_evento,
        lugar=solicitud.lugar,
        descripcion=solicitud.descripcion,
        estimacion_danos=solicitud.estimacion_danos,
    )
    return _traducir_errores_registro(
        lambda: servicio.registrar_manual(
            cliente_id=solicitud.cliente_id,
            registrado_por=asesor_id,
            solicitud=datos,
        )
    )


@router.get(
    "",
    response_model=list[Siniestro],
    summary="Lista siniestros del cliente autenticado o, para un asesor, de un cliente asociado",
)
def listar_siniestros(
    cliente_id: str | None = Query(
        default=None,
        description="Solo para ASESOR_VENTAS: cliente asociado del que se listan los siniestros.",
    ),
    usuario=Depends(get_current_user),
    servicio: ServicioSiniestros = Depends(obtener_servicio),
    asociaciones: RepositorioAsesorClientePostgres = Depends(obtener_asociaciones),
) -> list[Siniestro]:
    if usuario.rol == Rol.CLIENTE.value:
        return servicio.listar_de_cliente(str(usuario.id))

    if usuario.rol == Rol.ASESOR_VENTAS.value:
        if not cliente_id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "codigo": "CLIENTE_REQUERIDO",
                    "mensaje": "Indica el cliente del que quieres ver los siniestros.",
                },
            )
        if not asociaciones.existe_asociacion(str(usuario.id), cliente_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=CLIENTE_NO_ASOCIADO)
        return servicio.listar_de_cliente(cliente_id)

    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        detail={
            "codigo": "ACCESS_DENIED",
            "mensaje": "No tiene permisos para consultar siniestros.",
        },
    )
