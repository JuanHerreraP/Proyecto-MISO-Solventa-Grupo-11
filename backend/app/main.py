"""Punto de entrada del backend de Solventa."""

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app import __version__
from app.api import (
    autenticacion,
    autorizacion_socios,
    billetera,
    cotizaciones,
    credenciales_socios,
    enriquecimiento,
    identidad,
    oauth_socios,
    perfilamiento,
    salud,
    sesion_web,
    socios,
)
from app.identidad import (
    auditoria,
    modelos_db,  # noqa: F401
)
from app.identidad.web import opciones_cookie, origenes_web
from app.infraestructura.database import (
    Base,
    engine,
    esperar_base_disponible,
    preparar_esquema_registro,
)
from app.polizas import modelos_db as modelos_db_polizas  # noqa: F401
from app.socios import modelos_db as modelos_db_socios  # noqa: F401


def crear_app() -> FastAPI:
    opciones_cookie()
    esperar_base_disponible()
    Base.metadata.create_all(bind=engine)
    preparar_esquema_registro()

    app = FastAPI(
        title="Solventa API",
        version=__version__,
        description="Backend de la plataforma de seguros embebidos Solventa.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origenes_web(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Scope"],
    )

    @app.middleware("http")
    async def auditar_y_medir_latencia(request: Request, call_next):
        inicio = time.perf_counter()
        respuesta = await call_next(request)
        if request.url.path.startswith("/api/v1/auth/web/"):
            respuesta.headers["Cache-Control"] = "no-store"
            respuesta.headers["Pragma"] = "no-cache"
        if respuesta.status_code == 401 and "WWW-Authenticate" not in respuesta.headers:
            respuesta.headers["WWW-Authenticate"] = "Bearer"
        usuario = getattr(request.state, "usuario_autenticado", None)
        socio = getattr(request.state, "socio_autenticado", None)
        rechazo = respuesta.status_code in (401, 403)
        sensible = (
            request.method in ("POST", "PUT", "PATCH", "DELETE")
            or request.url.path == "/api/v1/auth/users"
            or request.url.path.startswith(
                (
                    "/api/v1/perfiles-riesgo",
                    "/api/v1/enriquecimientos",
                    "/api/v1/socios",
                    "/api/v1/billetera",
                )
            )
        )
        if not getattr(request.state, "evento_auth_registrado", False) and (rechazo or sensible):
            detalle = f"HTTP_{respuesta.status_code}"
            if socio is not None:
                detalle += f";socio:{socio.socio_id};tenant:{socio.tenant_id}"
            await run_in_threadpool(
                auditoria.registrar_evento_auth,
                tipo_evento=(
                    auditoria.TipoEventoAuth.ACCESS_DENIED
                    if rechazo
                    else auditoria.TipoEventoAuth.SENSITIVE_OPERATION
                ),
                exitoso=200 <= respuesta.status_code < 300,
                usuario_id=getattr(usuario, "id", None),
                email=getattr(usuario, "email", None),
                detalle=detalle,
                request=request,
            )
        respuesta.headers["X-Tiempo-Proceso-Ms"] = f"{(time.perf_counter() - inicio) * 1000:.3f}"
        return respuesta

    app.include_router(salud.router)
    app.include_router(cotizaciones.router)
    app.include_router(perfilamiento.router)
    app.include_router(enriquecimiento.router)
    app.include_router(socios.router)
    app.include_router(credenciales_socios.router)
    app.include_router(oauth_socios.router)
    app.include_router(autorizacion_socios.router)
    app.include_router(identidad.router)
    app.include_router(autenticacion.router)
    app.include_router(sesion_web.router)
    app.include_router(billetera.router)
    app.include_router(billetera.router_publico)
    return app


app = crear_app()
