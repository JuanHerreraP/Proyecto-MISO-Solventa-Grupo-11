"""Punto de entrada del backend de Solventa."""

import time

from fastapi import FastAPI, Request

from app import __version__
from app.api import (
    autenticacion,
    autorizacion_socios,
    enriquecimiento,
    identidad,
    perfilamiento,
    salud,
    socios,
)
from app.identidad import modelos_db  # noqa: F401
from app.infraestructura.database import Base, engine
from app.socios import modelos_db as modelos_db_socios  # noqa: F401


def crear_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)

    app = FastAPI(
        title="Solventa API",
        version=__version__,
        description="Backend de la plataforma de seguros embebidos Solventa.",
    )

    @app.middleware("http")
    async def medir_latencia(request: Request, call_next):
        inicio = time.perf_counter()
        respuesta = await call_next(request)
        respuesta.headers["X-Tiempo-Proceso-Ms"] = f"{(time.perf_counter() - inicio) * 1000:.3f}"
        return respuesta

    app.include_router(salud.router)
    app.include_router(perfilamiento.router)
    app.include_router(enriquecimiento.router)
    app.include_router(socios.router)
    app.include_router(autorizacion_socios.router)
    app.include_router(identidad.router)
    app.include_router(autenticacion.router)
    return app


app = crear_app()
