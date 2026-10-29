"""Pruebas de API del proveedor externo simulado de telemetría (HU20)."""

import pytest
from fastapi.testclient import TestClient

import mocks.telemetry.main as app_module
from mocks.telemetry.cliente_solventa import (
    ErrorEntregaSolventa,
    ErrorRespuestaSolventa,
)
from mocks.telemetry.main import app, obtener_cliente


class ClienteFalso:
    """Doble del cliente: registra lo enviado y devuelve un estado configurable."""

    def __init__(self, status_code: int = 200, error: Exception | None = None):
        self.status_code = status_code
        self.error = error
        self.enviados: list[dict] = []

    def enviar_evento(self, evento: dict) -> int:
        self.enviados.append(evento)
        if self.error is not None:
            raise self.error
        return self.status_code


@pytest.fixture
def entorno():
    # Almacén en memoria limpio por prueba para no filtrar eventos entre casos.
    app_module._eventos.clear()
    app_module._resultados.clear()
    cliente = ClienteFalso()
    app.dependency_overrides[obtener_cliente] = lambda: cliente
    yield TestClient(app), cliente
    app.dependency_overrides.clear()


VUELO = {
    "numero_vuelo": "AV123",
    "retraso_minutos": 215,
    "aeropuerto": "BOG",
    "fecha_evento": "2026-10-26T20:00:00Z",
}

CLIMA = {
    "ubicacion": "Bogotá",
    "tipo_medicion": "PRECIPITACION",
    "valor": 92.4,
    "unidad": "MM",
    "fecha_evento": "2026-10-26T18:00:00Z",
}


# --- Health -------------------------------------------------------------------------------


def test_health_responde_ok(entorno) -> None:
    cliente_http, cliente_solventa = entorno
    r = cliente_http.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "telemetry-provider"}
    # No debe contactar a Solventa.
    assert cliente_solventa.enviados == []


# --- Vuelo --------------------------------------------------------------------------------


def test_vuelo_valido_construye_evento_correcto(entorno) -> None:
    cliente_http, cliente_solventa = entorno

    r = cliente_http.post("/simulate/flight-delay", json=VUELO)

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["tipo_evento"] == "RETRASO_VUELO"
    assert cuerpo["enviado"] is True
    assert cuerpo["solventa_status"] == 200
    assert cuerpo["evento_id"].startswith("FLIGHT-AV123-20261026-")

    enviado = cliente_solventa.enviados[0]
    assert enviado["tipo_evento"] == "RETRASO_VUELO"
    assert enviado["numero_vuelo"] == "AV123"
    assert enviado["valor_observado"] == 215
    assert enviado["unidad"] == "MINUTOS"
    assert enviado["ubicacion"] == "BOG"
    assert enviado["fuente"] == "MOCK_FLIGHT_PROVIDER"
    assert enviado["evento_id"] == cuerpo["evento_id"]
    # El proveedor NO decide umbral: no aparece ninguna señal de siniestro.
    assert "crear_siniestro" not in enviado


def test_vuelo_no_confia_en_evento_id_del_cliente(entorno) -> None:
    cliente_http, _ = entorno
    r = cliente_http.post("/simulate/flight-delay", json={**VUELO, "evento_id": "HACKEADO"})
    # extra=forbid rechaza campos no declarados como evento_id.
    assert r.status_code == 422


def test_vuelo_retraso_negativo_responde_422(entorno) -> None:
    cliente_http, _ = entorno
    r = cliente_http.post("/simulate/flight-delay", json={**VUELO, "retraso_minutos": -5})
    assert r.status_code == 422


def test_vuelo_numero_vacio_responde_422(entorno) -> None:
    cliente_http, _ = entorno
    r = cliente_http.post("/simulate/flight-delay", json={**VUELO, "numero_vuelo": ""})
    assert r.status_code == 422


def test_vuelo_fecha_invalida_responde_422(entorno) -> None:
    cliente_http, _ = entorno
    r = cliente_http.post("/simulate/flight-delay", json={**VUELO, "fecha_evento": "no-es-fecha"})
    assert r.status_code == 422


# --- Clima --------------------------------------------------------------------------------


def test_clima_valido_construye_evento_correcto(entorno) -> None:
    cliente_http, cliente_solventa = entorno

    r = cliente_http.post("/simulate/weather-event", json=CLIMA)

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["tipo_evento"] == "EVENTO_CLIMATICO"
    assert cuerpo["evento_id"].startswith("WEATHER-BOGOTA-20261026-")

    enviado = cliente_solventa.enviados[0]
    assert enviado["tipo_evento"] == "EVENTO_CLIMATICO"
    assert enviado["ubicacion"] == "Bogotá"
    assert enviado["parametro"] == "PRECIPITACION"
    assert enviado["valor_observado"] == 92.4
    assert enviado["unidad"] == "MM"
    assert enviado["fuente"] == "MOCK_WEATHER_PROVIDER"


def test_clima_valor_negativo_responde_422(entorno) -> None:
    cliente_http, _ = entorno
    r = cliente_http.post("/simulate/weather-event", json={**CLIMA, "valor": -1})
    assert r.status_code == 422


def test_clima_ubicacion_vacia_responde_422(entorno) -> None:
    cliente_http, _ = entorno
    r = cliente_http.post("/simulate/weather-event", json={**CLIMA, "ubicacion": ""})
    assert r.status_code == 422


# --- Errores de Solventa ------------------------------------------------------------------


def test_solventa_no_disponible_responde_503(entorno) -> None:
    cliente_http, cliente_solventa = entorno
    cliente_solventa.error = ErrorEntregaSolventa("caído")
    r = cliente_http.post("/simulate/flight-delay", json=VUELO)
    assert r.status_code == 503
    assert r.json()["detail"]["codigo"] == "SOLVENTA_UNAVAILABLE"


def test_solventa_timeout_responde_503(entorno) -> None:
    cliente_http, cliente_solventa = entorno
    cliente_solventa.error = ErrorEntregaSolventa("timeout")
    r = cliente_http.post("/simulate/weather-event", json=CLIMA)
    assert r.status_code == 503
    assert r.json()["detail"]["codigo"] == "SOLVENTA_UNAVAILABLE"


def test_solventa_error_500_responde_502(entorno) -> None:
    cliente_http, cliente_solventa = entorno
    cliente_solventa.error = ErrorRespuestaSolventa(500, {"detail": "boom"})
    r = cliente_http.post("/simulate/flight-delay", json=VUELO)
    assert r.status_code == 502
    detalle = r.json()["detail"]
    assert detalle["codigo"] == "SOLVENTA_ERROR"
    assert detalle["solventa_status"] == 500


# --- Idempotencia / reenvío ---------------------------------------------------------------


def test_reenvio_conserva_el_mismo_evento_id(entorno) -> None:
    cliente_http, cliente_solventa = entorno

    primero = cliente_http.post("/simulate/flight-delay", json=VUELO).json()
    evento_id = primero["evento_id"]

    r = cliente_http.post(f"/simulate/retry/{evento_id}")

    assert r.status_code == 200
    assert r.json()["evento_id"] == evento_id
    # Se envió dos veces el MISMO identificador: Solventa puede detectar el duplicado.
    assert [e["evento_id"] for e in cliente_solventa.enviados] == [evento_id, evento_id]


def test_reenvio_de_evento_inexistente_responde_404(entorno) -> None:
    cliente_http, _ = entorno
    r = cliente_http.post("/simulate/retry/NO-EXISTE")
    assert r.status_code == 404
    assert r.json()["detail"]["codigo"] == "EVENTO_NO_ENCONTRADO"


def test_events_lista_los_generados(entorno) -> None:
    cliente_http, _ = entorno
    creado = cliente_http.post("/simulate/flight-delay", json=VUELO).json()
    r = cliente_http.get("/events")
    assert r.status_code == 200
    lista = r.json()
    assert len(lista) == 1
    assert lista[0]["evento_id"] == creado["evento_id"]
