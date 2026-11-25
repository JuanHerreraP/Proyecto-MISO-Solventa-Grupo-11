"""Proxy inverso al proveedor externo simulado de telemetría (HU20).

El proveedor de telemetría corre como contenedor acompañante del backend, escuchando solo en
`127.0.0.1:8004` dentro de la tarea ECS: nunca se expone directamente a Internet ni tiene su propio
balanceador. Para poder usar su Swagger desde fuera sin abrir un puerto público, el backend lo
publica de forma controlada bajo `/api/telemetry/*`, aprovechando el comportamiento `/api/*` que ya
existe en CloudFront y la API Gateway.

El proxy:

- Reenvía con httpx solo un conjunto cerrado de rutas y métodos (lista blanca). Cualquier otra ruta
  o método devuelve 404/405: no es un proxy abierto.
- Protege el acceso externo con HTTP Basic (usuario `TELEMETRY_MOCK_USUARIO`, por defecto
  `telemetry`, y contraseña `TELEMETRY_MOCK_PASSWORD`). Funciona con "Try it out" de Swagger (el
  navegador reenvía la credencial) y con Postman. Si no hay contraseña configurada (desarrollo
  local), la autenticación queda desactivada y el proxy sigue funcionando.
- No toca los proveedores KYC (8001-8003), que siguen siendo privados.

El proveedor de telemetría fija su `root_path` en `/api/telemetry`, de modo que el `openapi.json`
que entrega ya trae las URLs correctas y Swagger ejecuta las peticiones contra este proxy.
"""

import logging
import os
import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

logger = logging.getLogger(__name__)

PREFIJO = "/api/telemetry"

# A dónde reenvía el proxy. En AWS, el contenedor acompañante en la misma tarea.
UPSTREAM_POR_DEFECTO = "http://127.0.0.1:8004"

USUARIO_POR_DEFECTO = "telemetry"

# Encabezados que no deben reenviarse tal cual (los fija httpx o el servidor de destino).
_ENCABEZADOS_OMITIDOS = {
    "host",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "authorization",  # la credencial Basic es solo para el proxy; no se reenvía al proveedor.
}

# Lista blanca de rutas y métodos permitidos. La clave es el método; el valor, los prefijos de ruta
# (relativos al proveedor, sin el prefijo del proxy) permitidos para ese método.
_RUTAS_PERMITIDAS: dict[str, tuple[str, ...]] = {
    "GET": (
        "/docs",  # cubre /docs y /docs/oauth2-redirect
        "/redoc",
        "/openapi.json",
        "/health",
        "/events",
    ),
    "POST": (
        "/simulate/flight-delay",
        "/simulate/weather-event",
        "/simulate/retry/",  # /simulate/retry/{evento_id}
    ),
}

router = APIRouter(prefix=PREFIJO, tags=["telemetria-proxy"])

_seguridad = HTTPBasic(auto_error=False)


def _upstream() -> str:
    return os.getenv("TELEMETRY_UPSTREAM_URL", UPSTREAM_POR_DEFECTO).rstrip("/")


def _password_esperada() -> str | None:
    valor = os.getenv("TELEMETRY_MOCK_PASSWORD", "").strip()
    return valor or None


def _usuario_esperado() -> str:
    return os.getenv("TELEMETRY_MOCK_USUARIO", USUARIO_POR_DEFECTO).strip() or USUARIO_POR_DEFECTO


def verificar_basic(
    credenciales: HTTPBasicCredentials | None = Depends(_seguridad),
) -> None:
    """Exige HTTP Basic cuando hay contraseña configurada. Comparación en tiempo constante."""
    password = _password_esperada()
    if password is None:
        # Sin contraseña configurada (desarrollo local): no se exige autenticación.
        return
    usuario = _usuario_esperado()
    if credenciales is None:
        usuario_ok = False
        password_ok = False
    else:
        usuario_ok = secrets.compare_digest(credenciales.username, usuario)
        password_ok = secrets.compare_digest(credenciales.password, password)
    if not (usuario_ok and password_ok):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales del proveedor de telemetría ausentes o inválidas.",
            headers={"WWW-Authenticate": 'Basic realm="telemetry"'},
        )


def _ruta_permitida(metodo: str, ruta: str) -> bool:
    prefijos = _RUTAS_PERMITIDAS.get(metodo.upper())
    if not prefijos:
        return False
    return any(ruta == p or ruta.startswith(p) for p in prefijos)


@router.api_route(
    "/{ruta:path}",
    methods=["GET", "POST"],
    include_in_schema=False,
    dependencies=[Depends(verificar_basic)],
)
async def proxy(ruta: str, request: Request) -> Response:
    """Reenvía la petición al proveedor de telemetría si está en la lista blanca."""
    ruta_normalizada = "/" + ruta.lstrip("/")
    metodo = request.method.upper()

    if metodo not in _RUTAS_PERMITIDAS:
        raise HTTPException(status.HTTP_405_METHOD_NOT_ALLOWED, detail="Método no permitido.")
    if not _ruta_permitida(metodo, ruta_normalizada):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ruta no disponible.")

    destino = f"{_upstream()}{ruta_normalizada}"
    cuerpo = await request.body()
    encabezados = {
        clave: valor
        for clave, valor in request.headers.items()
        if clave.lower() not in _ENCABEZADOS_OMITIDOS
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as cliente:
            respuesta = await cliente.request(
                metodo,
                destino,
                params=dict(request.query_params),
                content=cuerpo,
                headers=encabezados,
            )
    except httpx.HTTPError as error:
        logger.warning("El proveedor de telemetría no respondió (%s): %s", destino, error)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="El proveedor de telemetría no está disponible.",
        ) from error

    # Se omiten los encabezados de transporte del proveedor para no romper la respuesta del backend.
    # `content-encoding` también: httpx ya devolvió el cuerpo descomprimido en `respuesta.content`.
    omitidos_respuesta = _ENCABEZADOS_OMITIDOS | {"content-encoding"}
    encabezados_respuesta = {
        clave: valor
        for clave, valor in respuesta.headers.items()
        if clave.lower() not in omitidos_respuesta
    }
    return Response(
        content=respuesta.content,
        status_code=respuesta.status_code,
        headers=encabezados_respuesta,
        media_type=respuesta.headers.get("content-type"),
    )
