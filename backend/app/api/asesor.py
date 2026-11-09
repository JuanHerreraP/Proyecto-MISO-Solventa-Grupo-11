"""API para que el asesor de ventas gestione sus clientes (HU20).

El asesor se asocia a un cliente (por correo) y lista los clientes que atiende. Solo el
rol ASESOR_VENTAS puede usar estos endpoints. El `asesor_id` sale siempre de la sesión.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.seguridad import requiere_roles
from app.identidad.asociacion import (
    ClienteDeAsesor,
    RepositorioAsesorClientePostgres,
)
from app.identidad.modelos import Rol
from app.identidad.repositorio import RepositorioUsuariosPostgres
from app.infraestructura.database import get_db
from app.polizas.repositorio import RepositorioEnlacesPostgres, RepositorioPolizasPostgres
from app.polizas.servicio import ServicioBilletera
from app.polizas.vistas import Billetera

router = APIRouter(prefix="/api/v1/asesor", tags=["asesor"])

asesor_actual = requiere_roles(Rol.ASESOR_VENTAS.value)

CLIENTE_NO_ASOCIADO = {
    "codigo": "CLIENTE_NO_ASOCIADO",
    "mensaje": "El cliente no está asociado a tu cuenta de asesor.",
}


class SolicitudAsociarCliente(BaseModel):
    """El asesor asocia a un cliente identificándolo por su correo."""

    email: EmailStr


@router.get(
    "/clientes",
    response_model=list[ClienteDeAsesor],
    summary="Lista los clientes asociados al asesor autenticado",
)
def listar_clientes(
    usuario=Depends(asesor_actual),
    db: Session = Depends(get_db),
) -> list[ClienteDeAsesor]:
    repositorio = RepositorioAsesorClientePostgres(db)
    return repositorio.listar_clientes_de_asesor(str(usuario.id))


@router.post(
    "/clientes",
    response_model=ClienteDeAsesor,
    status_code=status.HTTP_201_CREATED,
    summary="Asocia un cliente (por correo) al asesor autenticado",
    responses={
        404: {"description": "No existe un cliente con ese correo."},
        409: {"description": "El cliente ya estaba asociado al asesor."},
    },
)
def asociar_cliente(
    solicitud: SolicitudAsociarCliente,
    usuario=Depends(asesor_actual),
    db: Session = Depends(get_db),
) -> ClienteDeAsesor:
    usuarios = RepositorioUsuariosPostgres(db)
    cliente = usuarios.buscar_por_email(str(solicitud.email))
    if cliente is None or cliente.rol != Rol.CLIENTE.value:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "codigo": "CLIENTE_NO_ENCONTRADO",
                "mensaje": "No existe un cliente con ese correo.",
            },
        )

    asociaciones = RepositorioAsesorClientePostgres(db)
    asesor_id = str(usuario.id)
    cliente_id = str(cliente.id)
    if asociaciones.existe_asociacion(asesor_id, cliente_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "codigo": "CLIENTE_YA_ASOCIADO",
                "mensaje": "El cliente ya está asociado a tu cuenta.",
            },
        )

    asociaciones.asociar(asesor_id, cliente_id)
    return ClienteDeAsesor(
        cliente_id=cliente_id,
        nombre=cliente.nombre,
        apellido=cliente.apellido,
        email=cliente.email,
    )


@router.get(
    "/clientes/{cliente_id}/polizas",
    response_model=Billetera,
    summary="Lista las pólizas de un cliente asociado, para elegir la afectada en un siniestro",
    responses={403: {"description": "El cliente no está asociado al asesor."}},
)
def listar_polizas_de_cliente(
    cliente_id: str,
    usuario=Depends(asesor_actual),
    db: Session = Depends(get_db),
) -> Billetera:
    asociaciones = RepositorioAsesorClientePostgres(db)
    if not asociaciones.existe_asociacion(str(usuario.id), cliente_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=CLIENTE_NO_ASOCIADO)

    servicio = ServicioBilletera(
        RepositorioPolizasPostgres(db),
        RepositorioEnlacesPostgres(db),
    )
    return servicio.billetera(cliente_id)
