"""API de apoyo para el analista de cumplimiento (HU25 / CPM-72).

Expone un único resolutor de pólizas: dado un identificador que puede ser el `poliza_id` o el
`numero_poliza`, devuelve los datos mínimos para que el frontend del auditor obtenga el
`poliza_id` y luego consulte `GET /api/v1/polizas/{poliza_id}/historial`.

Es estrictamente de lectura y deliberadamente limitado: NO lista pólizas, NO busca por cliente
y NO devuelve colecciones. Solo resuelve una póliza concreta. Solo el rol
`ANALISTA_CUMPLIMIENTO` puede usarlo.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.seguridad import requiere_roles
from app.identidad.modelos import Rol
from app.infraestructura.database import get_db
from app.polizas.dominio.modelos import hoy_en_colombia
from app.polizas.repositorio import RepositorioPolizas, RepositorioPolizasPostgres

router = APIRouter(prefix="/api/v1/auditoria", tags=["auditoria"])

auditor_actual = requiere_roles(Rol.ANALISTA_CUMPLIMIENTO.value)


class PolizaResuelta(BaseModel):
    """Datos mínimos para situar una póliza antes de consultar su historial (HU25 §8)."""

    model_config = ConfigDict(extra="forbid")

    poliza_id: str
    numero_poliza: str
    cliente_id: str
    nombre_ramo: str
    estado: str


def obtener_repositorio(db: Session = Depends(get_db)) -> RepositorioPolizas:
    return RepositorioPolizasPostgres(db)


@router.get(
    "/polizas/{identificador}",
    response_model=PolizaResuelta,
    summary="Resuelve una póliza por poliza_id o numero_poliza (solo auditoría)",
    responses={
        403: {"description": "El rol no tiene acceso a la consulta de auditoría."},
        404: {"description": "No existe una póliza con ese identificador."},
    },
)
def resolver_poliza(
    identificador: str,
    respuesta: Response,
    _=Depends(auditor_actual),
    repositorio: RepositorioPolizas = Depends(obtener_repositorio),
) -> PolizaResuelta:
    respuesta.headers["Cache-Control"] = "no-store"

    identificador = identificador.strip()
    poliza = repositorio.obtener(identificador) or repositorio.buscar_por_numero(identificador)
    if poliza is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"codigo": "POLIZA_NO_ENCONTRADA", "mensaje": "La póliza no existe."},
        )

    return PolizaResuelta(
        poliza_id=poliza.poliza_id,
        numero_poliza=poliza.numero_poliza,
        cliente_id=poliza.cliente_id,
        nombre_ramo=poliza.nombre_ramo,
        estado=poliza.estado_en(hoy_en_colombia(datetime.now(UTC))).value,
    )
