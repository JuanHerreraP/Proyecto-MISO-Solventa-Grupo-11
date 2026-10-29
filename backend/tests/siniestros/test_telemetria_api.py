"""Pruebas del endpoint de integración de telemetría externa (HU20).

Solventa recibe la observación y decide: compara el valor observado contra el umbral contratado,
respeta la vigencia de la póliza y es idempotente por `evento_id`.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.telemetria import obtener_servicio, verificar_api_key
from app.main import app
from app.polizas.dominio.modelos import CoberturaPoliza, RamoPoliza
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from app.siniestros.repositorio import RepositorioSiniestrosEnMemoria
from app.siniestros.telemetria import ServicioTelemetria
from tests.billetera.fabrica import poliza

RUTA = "/api/v1/integraciones/telemetria/eventos"
# 2026-10-26 en Bogotá; la póliza paramétrica va del 2026-10-06 al 2026-11-05.
AHORA = datetime(2026, 10, 26, 20, 0, tzinfo=UTC)

CONDICION_VUELO = (
    "tipo_evento=RETRASO_VUELO; numero_vuelo=AV123; ubicacion=BOG; "
    "umbral_disparo=180; unidad=MINUTOS"
)
CONDICION_CLIMA = (
    "tipo_evento=EVENTO_CLIMATICO; ubicacion=Bogotá; parametro=PRECIPITACION; "
    "umbral_disparo=80; unidad=MM"
)


def poliza_parametrica(descripcion: str, **cambios) -> "object":
    base = {
        "poliza_id": "POL-PM",
        "numero_poliza": "SOL-PM-000001",
        "ramo": RamoPoliza.PARAMETRICO,
        "fecha_inicio": date(2026, 10, 6),
        "fecha_fin": date(2026, 11, 5),
        "cobertura_principal": CoberturaPoliza(
            codigo="RETRASO_DE_VUELO",
            nombre="Retraso de vuelo",
            suma_asegurada=Decimal("500000.00"),
            descripcion=descripcion,
        ),
    }
    base.update(cambios)
    return poliza(**base)


@pytest.fixture
def entorno():
    polizas = RepositorioPolizasEnMemoria()
    siniestros = RepositorioSiniestrosEnMemoria()
    servicio = ServicioTelemetria(siniestros, polizas, reloj=lambda: AHORA)
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    # Por defecto la API Key es válida; los casos de auth la sobreescriben o la quitan.
    app.dependency_overrides[verificar_api_key] = lambda: None
    yield TestClient(app), polizas, siniestros
    app.dependency_overrides.clear()


def evento_vuelo(**cambios) -> dict:
    datos = {
        "evento_id": "FLIGHT-AV123-20261026-abc",
        "tipo_evento": "RETRASO_VUELO",
        "numero_vuelo": "AV123",
        "valor_observado": 215,
        "unidad": "MINUTOS",
        "ubicacion": "BOG",
        "fecha_evento": "2026-10-26T20:00:00Z",
        "fuente": "MOCK_FLIGHT_PROVIDER",
    }
    datos.update(cambios)
    return datos


def evento_clima(**cambios) -> dict:
    datos = {
        "evento_id": "WEATHER-BOGOTA-20261026-xyz",
        "tipo_evento": "EVENTO_CLIMATICO",
        "ubicacion": "Bogotá",
        "parametro": "PRECIPITACION",
        "valor_observado": 92.4,
        "unidad": "MM",
        "fecha_evento": "2026-10-26T18:00:00Z",
        "fuente": "MOCK_WEATHER_PROVIDER",
    }
    datos.update(cambios)
    return datos


# --- Autenticación ------------------------------------------------------------------------


def test_sin_api_key_responde_401() -> None:
    # Sin override de verificar_api_key se exige la credencial real.
    app.dependency_overrides.clear()
    r = TestClient(app).post(RUTA, json=evento_vuelo())
    assert r.status_code == 401
    assert r.json()["detail"]["codigo"] == "API_KEY_INVALIDA"


def test_api_key_incorrecta_responde_401(monkeypatch) -> None:
    app.dependency_overrides.clear()
    monkeypatch.setenv("SOLVENTA_TELEMETRY_API_KEY", "la-correcta")
    r = TestClient(app).post(RUTA, json=evento_vuelo(), headers={"X-API-Key": "otra"})
    assert r.status_code == 401


def test_api_key_correcta_pasa_auth(entorno, monkeypatch) -> None:
    cliente, _, _ = entorno
    # Mantener el servicio en memoria (vía fixture) y validar la API Key real.
    app.dependency_overrides.pop(verificar_api_key, None)
    monkeypatch.setenv("SOLVENTA_TELEMETRY_API_KEY", "la-correcta")
    # Sin pólizas sembradas en el repo en memoria: auth pasa y el resultado es SIN_COBERTURA.
    r = cliente.post(RUTA, json=evento_vuelo(), headers={"X-API-Key": "la-correcta"})
    assert r.status_code == 200
    assert r.json()["resultado"] == "SIN_COBERTURA"


# --- Decisión de Solventa -----------------------------------------------------------------


def test_vuelo_bajo_umbral_no_crea_siniestro(entorno) -> None:
    cliente, polizas, siniestros = entorno
    polizas.guardar(poliza_parametrica(CONDICION_VUELO))

    r = cliente.post(RUTA, json=evento_vuelo(valor_observado=120))

    assert r.status_code == 200
    assert r.json()["resultado"] == "SIN_COBERTURA"
    assert siniestros.obtener_por_evento("FLIGHT-AV123-20261026-abc") is None


def test_vuelo_sobre_umbral_crea_siniestro_automatico(entorno) -> None:
    cliente, polizas, siniestros = entorno
    polizas.guardar(poliza_parametrica(CONDICION_VUELO))

    r = cliente.post(RUTA, json=evento_vuelo(valor_observado=215))

    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["resultado"] == "SINIESTRO_CREADO"
    assert cuerpo["poliza_id"] == "POL-PM"
    creado = siniestros.obtener(cuerpo["siniestro_id"])
    assert creado is not None
    assert creado.origen.value == "AUTOMATICO"
    assert creado.evento_id == "FLIGHT-AV123-20261026-abc"
    assert creado.estimacion_danos == Decimal("500000.00")
    assert creado.cliente_id == "CLI-001"


def test_vuelo_distinto_no_aplica(entorno) -> None:
    cliente, polizas, siniestros = entorno
    polizas.guardar(poliza_parametrica(CONDICION_VUELO))
    # Mismo tipo de evento pero otro número de vuelo: la póliza no aplica.
    r = cliente.post(RUTA, json=evento_vuelo(numero_vuelo="LA999", valor_observado=500))
    assert r.status_code == 200
    assert r.json()["resultado"] == "SIN_COBERTURA"


def test_poliza_parametrica_vencida_no_crea_siniestro(entorno) -> None:
    cliente, polizas, _ = entorno
    polizas.guardar(
        poliza_parametrica(
            CONDICION_VUELO,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 9, 30),
        )
    )
    r = cliente.post(RUTA, json=evento_vuelo(valor_observado=215))
    assert r.status_code == 200
    assert r.json()["resultado"] == "SIN_COBERTURA"


def test_clima_sobre_umbral_crea_siniestro(entorno) -> None:
    cliente, polizas, siniestros = entorno
    polizas.guardar(
        poliza_parametrica(
            CONDICION_CLIMA,
            poliza_id="POL-CLIMA",
            numero_poliza="SOL-PM-000002",
        )
    )

    r = cliente.post(RUTA, json=evento_clima(valor_observado=92.4))

    assert r.status_code == 201
    creado = siniestros.obtener(r.json()["siniestro_id"])
    assert creado is not None
    assert creado.evento_id == "WEATHER-BOGOTA-20261026-xyz"


# --- Idempotencia -------------------------------------------------------------------------


def test_reenvio_mismo_evento_no_duplica_siniestro(entorno) -> None:
    cliente, polizas, siniestros = entorno
    polizas.guardar(poliza_parametrica(CONDICION_VUELO))

    primero = cliente.post(RUTA, json=evento_vuelo(valor_observado=215))
    assert primero.status_code == 201
    siniestro_id = primero.json()["siniestro_id"]

    segundo = cliente.post(RUTA, json=evento_vuelo(valor_observado=215))

    assert segundo.status_code == 200
    cuerpo = segundo.json()
    assert cuerpo["resultado"] == "DUPLICADO"
    assert cuerpo["siniestro_id"] == siniestro_id
    # Solo existe un siniestro para ese cliente.
    assert len(siniestros.listar_por_cliente("CLI-001")) == 1


# --- Validación ---------------------------------------------------------------------------


def test_evento_sin_evento_id_responde_422(entorno) -> None:
    cliente, _, _ = entorno
    cuerpo = evento_vuelo()
    del cuerpo["evento_id"]
    r = cliente.post(RUTA, json=cuerpo)
    assert r.status_code == 422
