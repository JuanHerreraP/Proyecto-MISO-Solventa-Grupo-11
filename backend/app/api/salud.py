"""Endpoint de salud usado por el balanceador y por el pipeline de despliegue."""

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__

router = APIRouter(tags=["salud"])


class EstadoSalud(BaseModel):
    estado: str
    servicio: str
    version: str


@router.get("/salud", response_model=EstadoSalud)
def salud() -> EstadoSalud:
    return EstadoSalud(estado="ok", servicio="solventa-backend", version=__version__)
