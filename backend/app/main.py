"""Punto de entrada del backend de Solventa."""

import time

from fastapi import FastAPI, Request

from app import __version__
from app.api import perfilamiento, salud


def crear_app() -> FastAPI:
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
    return app


app = crear_app()
