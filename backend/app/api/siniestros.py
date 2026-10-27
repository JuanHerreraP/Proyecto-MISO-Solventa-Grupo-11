"""API del registro manual de siniestros (HU20).

El router solo autentica, valida el rol, delega en el servicio y traduce las excepciones de
dominio a códigos HTTP. El `cliente_id` se toma de la sesión, nunca del cuerpo.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.seguridad import get_current_user
from app.identidad.modelos import Rol
from app.infraestructura.database import get_db
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.siniestros.modelos import Siniestro, SolicitudSiniestro
from app.siniestros.repositorio import RepositorioSiniestrosPostgres
from app.siniestros.servicio import (
    FechaEventoInvalida,
    PolizaAjena,
    PolizaNoEncontrada,
    PolizaNoVigente,
    ServicioSiniestros,
)

router = APIRouter(prefix="/api/v1/siniestros", tags=["siniestros"])


def obtener_servicio(db: Session = Depends(get_db)) -> ServicioSiniestros:
    return ServicioSiniestros(
        siniestros=RepositorioSiniestrosPostgres(db),
        polizas=RepositorioPolizasPostgres(db),
    )


@router.post(
    "",
    response_model=Siniestro,
    status_code=status.HTTP_201_CREATED,
    summary="Registra manualmente un siniestro sobre una póliza vigente del cliente",
    responses={
        403: {"description": "La póliza no pertenece al cliente autenticado."},
        404: {"description": "La póliza no existe."},
        409: {"description": "La póliza no está vigente."},
        422: {"description": "La fecha del evento es futura o está fuera de la vigencia."},
    },
)
def registrar_siniestro(
    solicitud: SolicitudSiniestro,
    usuario=Depends(get_current_user),
    servicio: ServicioSiniestros = Depends(obtener_servicio),
) -> Siniestro:
    # Por ahora solo el cliente asegurado registra sobre sus propias pólizas. El modelo ya
    # permite que un asesor registre a nombre de otro cliente (cliente_id != registrado_por).
    if usuario.rol != Rol.CLIENTE.value:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "codigo": "ACCESS_DENIED",
                "mensaje": "Solo el cliente asegurado puede registrar su siniestro.",
            },
        )

    cliente_id = str(usuario.id)
    try:
        return servicio.registrar_manual(
            cliente_id=cliente_id,
            registrado_por=cliente_id,
            solicitud=solicitud,
        )
    except PolizaNoEncontrada:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"codigo": "POLIZA_NO_ENCONTRADA", "mensaje": "La póliza no existe."},
        ) from None
    except PolizaAjena:
        # Se responde 403 como pide la HU; no se distingue de una póliza inexistente ajena.
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "codigo": "POLIZA_AJENA",
                "mensaje": "No tiene acceso a esta póliza.",
            },
        ) from None
    except PolizaNoVigente:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "codigo": "POLIZA_NO_VIGENTE",
                "mensaje": "La póliza no está vigente.",
            },
        ) from None
    except FechaEventoInvalida as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"codigo": error.codigo, "mensaje": error.mensaje},
        ) from None


@router.get(
    "",
    response_model=list[Siniestro],
    summary="Lista los siniestros del cliente autenticado, del más reciente al más antiguo",
)
def listar_siniestros(
    usuario=Depends(get_current_user),
    servicio: ServicioSiniestros = Depends(obtener_servicio),
) -> list[Siniestro]:
    if usuario.rol != Rol.CLIENTE.value:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "codigo": "ACCESS_DENIED",
                "mensaje": "Solo el cliente asegurado puede consultar sus siniestros.",
            },
        )
    return servicio.listar_de_cliente(str(usuario.id))
