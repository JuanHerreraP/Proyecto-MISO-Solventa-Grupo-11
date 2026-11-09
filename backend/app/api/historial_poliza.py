"""API del historial consolidado de movimientos de una póliza (HU25 / CPM-72).

Solo lectura: el router autentica, decide el alcance según el rol, delega en el servicio y
traduce las excepciones de dominio a códigos HTTP. No expone endpoints de escritura.

Alcance por rol:
- CLIENTE: solo el historial de sus propias pólizas (se filtra por `cliente_id` de la sesión).
- Roles internos de solo lectura (SERVICIO_INTERNO, OPERACIONES_SINIESTROS): cualquier póliza,
  como apoyo de auditoría/cumplimiento. El proyecto aún no tiene un rol AUDITOR dedicado; cuando
  exista, basta añadirlo a `ROLES_LECTURA_INTERNA`.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.seguridad import get_current_user
from app.desembolsos.repositorio import RepositorioDesembolsosPostgres
from app.identidad.modelos import Rol
from app.infraestructura.database import get_db
from app.pagos.repositorio import RepositorioPagosPostgres
from app.polizas.historial import (
    AccesoDenegadoHistorial,
    PolizaNoEncontrada,
    ServicioHistorialPoliza,
)
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.polizas.repositorio_endosos import RepositorioEndososPostgres
from app.polizas.vistas_historial import HistorialPoliza

router = APIRouter(prefix="/api/v1/polizas", tags=["historial"])

# Roles internos con acceso de solo lectura al historial de cualquier póliza (HU25 §26).
ROLES_LECTURA_INTERNA = frozenset({Rol.SERVICIO_INTERNO.value, Rol.OPERACIONES_SINIESTROS.value})


def obtener_servicio(db: Session = Depends(get_db)) -> ServicioHistorialPoliza:
    return ServicioHistorialPoliza(
        polizas=RepositorioPolizasPostgres(db),
        pagos=RepositorioPagosPostgres(db),
        endosos=RepositorioEndososPostgres(db),
        desembolsos=RepositorioDesembolsosPostgres(db),
    )


@router.get(
    "/{poliza_id}/historial",
    response_model=HistorialPoliza,
    summary="Bitácora de movimientos de la póliza, del más reciente al más antiguo",
    responses={
        403: {"description": "La póliza es de otro cliente o el rol no tiene acceso."},
        404: {"description": "La póliza no existe."},
    },
)
def consultar_historial(
    poliza_id: str,
    respuesta: Response,
    usuario=Depends(get_current_user),
    servicio: ServicioHistorialPoliza = Depends(obtener_servicio),
) -> HistorialPoliza:
    respuesta.headers["Cache-Control"] = "no-store"

    if usuario.rol == Rol.CLIENTE.value:
        cliente_id: str | None = str(usuario.id)
    elif usuario.rol in ROLES_LECTURA_INTERNA:
        cliente_id = None
    else:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "codigo": "ACCESS_DENIED",
                "mensaje": "No tiene permisos para consultar el historial de la póliza.",
            },
        )

    try:
        return servicio.consultar(poliza_id, cliente_id)
    except PolizaNoEncontrada:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"codigo": "POLIZA_NO_ENCONTRADA", "mensaje": "La póliza no existe."},
        ) from None
    except AccesoDenegadoHistorial:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"codigo": "ACCESS_DENIED", "mensaje": "No tiene acceso a esta póliza."},
        ) from None
