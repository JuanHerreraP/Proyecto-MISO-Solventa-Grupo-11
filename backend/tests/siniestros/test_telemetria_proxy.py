"""Pruebas del proxy inverso al proveedor de telemetría (HU20).

El proxy publica el proveedor (que corre en 127.0.0.1:8004) bajo `/api/telemetry/*`, protegido con
HTTP Basic y limitado a una lista blanca de rutas y métodos. Estas pruebas no levantan el proveedor
real: sustituyen el cliente httpx por un doble que registra la petición reenviada.
"""

import httpx
import pytest
from fastapi.testclient import TestClient

import app.api.telemetria_proxy as proxy
from app.main import app

USUARIO = "telemetry"
PASSWORD = "super-secreta-para-pruebas"


class RespuestaFalsa:
    def __init__(self, status_code=200, content=b'{"ok": true}', headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {"content-type": "application/json"}


class ClienteHttpxFalso:
    """Doble de httpx.AsyncClient que registra la última petición reenviada."""

    ultima = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def request(self, metodo, url, params=None, content=None, headers=None):
        ClienteHttpxFalso.ultima = {
            "metodo": metodo,
            "url": url,
            "params": params,
            "content": content,
            "headers": headers,
        }
        return RespuestaFalsa()


@pytest.fixture
def cliente_con_auth(monkeypatch):
    monkeypatch.setenv("TELEMETRY_MOCK_PASSWORD", PASSWORD)
    monkeypatch.setenv("TELEMETRY_UPSTREAM_URL", "http://127.0.0.1:8004")
    monkeypatch.setattr(proxy.httpx, "AsyncClient", ClienteHttpxFalso)
    ClienteHttpxFalso.ultima = None
    return TestClient(app)


@pytest.fixture
def cliente_sin_auth(monkeypatch):
    # Sin contraseña configurada: la autenticación queda desactivada (modo local).
    monkeypatch.delenv("TELEMETRY_MOCK_PASSWORD", raising=False)
    monkeypatch.setattr(proxy.httpx, "AsyncClient", ClienteHttpxFalso)
    ClienteHttpxFalso.ultima = None
    return TestClient(app)


# --- Autenticación ------------------------------------------------------------------------


def test_sin_credenciales_responde_401(cliente_con_auth) -> None:
    r = cliente_con_auth.get("/api/telemetry/health")
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"].startswith("Basic")


def test_credenciales_invalidas_responde_401(cliente_con_auth) -> None:
    r = cliente_con_auth.get("/api/telemetry/health", auth=("telemetry", "mala"))
    assert r.status_code == 401


def test_credenciales_validas_reenvian(cliente_con_auth) -> None:
    r = cliente_con_auth.get("/api/telemetry/health", auth=(USUARIO, PASSWORD))
    assert r.status_code == 200
    assert ClienteHttpxFalso.ultima["metodo"] == "GET"
    assert ClienteHttpxFalso.ultima["url"] == "http://127.0.0.1:8004/health"
    # La credencial Basic del proxy NO se reenvía al proveedor.
    cabeceras = {k.lower() for k in ClienteHttpxFalso.ultima["headers"]}
    assert "authorization" not in cabeceras


def test_sin_password_configurada_no_exige_auth(cliente_sin_auth) -> None:
    r = cliente_sin_auth.get("/api/telemetry/health")
    assert r.status_code == 200
    assert ClienteHttpxFalso.ultima["url"] == "http://127.0.0.1:8004/health"


# --- Lista blanca de rutas y métodos ------------------------------------------------------


def test_ruta_fuera_de_lista_blanca_responde_404(cliente_con_auth) -> None:
    r = cliente_con_auth.get("/api/telemetry/secreto", auth=(USUARIO, PASSWORD))
    assert r.status_code == 404
    assert ClienteHttpxFalso.ultima is None


def test_metodo_no_permitido_responde_405(cliente_con_auth) -> None:
    # DELETE no está en la lista blanca; el router solo acepta GET/POST en el proxy.
    r = cliente_con_auth.request("DELETE", "/api/telemetry/events", auth=(USUARIO, PASSWORD))
    assert r.status_code in (404, 405)
    assert ClienteHttpxFalso.ultima is None


def test_post_simular_vuelo_se_reenvia(cliente_con_auth) -> None:
    r = cliente_con_auth.post(
        "/api/telemetry/simulate/flight-delay",
        json={"numero_vuelo": "AV1"},
        auth=(USUARIO, PASSWORD),
    )
    assert r.status_code == 200
    assert ClienteHttpxFalso.ultima["metodo"] == "POST"
    assert ClienteHttpxFalso.ultima["url"].endswith("/simulate/flight-delay")


def test_post_retry_con_id_se_reenvia(cliente_con_auth) -> None:
    r = cliente_con_auth.post(
        "/api/telemetry/simulate/retry/FLIGHT-123",
        auth=(USUARIO, PASSWORD),
    )
    assert r.status_code == 200
    assert ClienteHttpxFalso.ultima["url"].endswith("/simulate/retry/FLIGHT-123")


def test_docs_y_openapi_se_reenvian(cliente_con_auth) -> None:
    for ruta in ("/api/telemetry/docs", "/api/telemetry/openapi.json", "/api/telemetry/redoc"):
        ClienteHttpxFalso.ultima = None
        r = cliente_con_auth.get(ruta, auth=(USUARIO, PASSWORD))
        assert r.status_code == 200
        assert ClienteHttpxFalso.ultima is not None


# --- Proveedor caído ----------------------------------------------------------------------


def test_proveedor_caido_responde_502(cliente_con_auth, monkeypatch) -> None:
    class ClienteQueFalla(ClienteHttpxFalso):
        async def request(self, *args, **kwargs):
            raise httpx.ConnectError("sin conexión")

    monkeypatch.setattr(proxy.httpx, "AsyncClient", ClienteQueFalla)
    r = cliente_con_auth.get("/api/telemetry/health", auth=(USUARIO, PASSWORD))
    assert r.status_code == 502
