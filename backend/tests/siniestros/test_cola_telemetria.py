"""Pruebas del MVP de contrapresión con cola para la telemetría paramétrica (HU20).

Cubre:
- El publicador en memoria.
- El endpoint: responde 202 cuando la cola acepta y 503 cuando el publicador falla.
- El worker: procesa un mensaje y crea el siniestro con el desembolso APAGADO (al_crear=None,
  nunca se ordena desembolso) y es idempotente por `evento_id`.
"""

import json
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.telemetria import (
    obtener_metricas,
    obtener_publicador,
    verificar_api_key,
)
from app.main import app
from app.polizas.dominio.modelos import CoberturaPoliza, RamoPoliza
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from app.siniestros import worker as worker_mod
from app.siniestros.cola import (
    PublicacionFallida,
    PublicadorEnMemoria,
    PublicadorSQS,
)
from app.siniestros.repositorio import RepositorioSiniestrosEnMemoria
from tests.billetera.fabrica import poliza

RUTA = "/api/v1/integraciones/telemetria/eventos"
AHORA = datetime(2026, 10, 26, 20, 0, tzinfo=UTC)

CONDICION_VUELO = (
    "tipo_evento=RETRASO_VUELO; numero_vuelo=AV123; ubicacion=BOG; "
    "umbral_disparo=180; unidad=MINUTOS"
)


def poliza_parametrica(**cambios):
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
            descripcion=CONDICION_VUELO,
        ),
    }
    base.update(cambios)
    return poliza(**base)


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


class _PublicadorQueFalla:
    def publicar(self, evento: dict) -> str:
        raise PublicacionFallida("SQS rechazó el evento (simulado).")


class _MetricasFalsas:
    def __init__(self):
        self.contados: list[str] = []

    def contar(self, metrica: str, valor: float = 1.0) -> None:
        self.contados.append(metrica)


# --- Publicador en memoria ----------------------------------------------------------------


def test_publicador_en_memoria_guarda_y_devuelve_message_id():
    pub = PublicadorEnMemoria()
    mid1 = pub.publicar({"evento_id": "E-1"})
    mid2 = pub.publicar({"evento_id": "E-2"})
    assert mid1 == "mem-1"
    assert mid2 == "mem-2"
    assert [m["evento_id"] for m in pub.mensajes] == ["E-1", "E-2"]


def test_publicador_sqs_falla_si_no_hay_message_id():
    class _SinMessageId:
        def send_message(self, **_):
            return {}

    pub = PublicadorSQS(url_cola="https://sqs/x", cliente=_SinMessageId())
    with pytest.raises(PublicacionFallida):
        pub.publicar({"evento_id": "E-1"})


def test_publicador_sqs_devuelve_message_id_del_transporte():
    class _OK:
        def send_message(self, **_):
            return {"MessageId": "abc-123"}

    pub = PublicadorSQS(url_cola="https://sqs/x", cliente=_OK())
    assert pub.publicar({"evento_id": "E-1"}) == "abc-123"


# --- Endpoint: contrapresión (modo asíncrono) ---------------------------------------------


@pytest.fixture
def cliente_asincrono(monkeypatch):
    monkeypatch.setenv("EC_MODO_SINCRONO", "false")
    monkeypatch.setenv("EC_METRICAS", "false")
    app.dependency_overrides[verificar_api_key] = lambda: None
    metricas = _MetricasFalsas()
    app.dependency_overrides[obtener_metricas] = lambda: metricas
    yield TestClient(app), metricas
    app.dependency_overrides.clear()


def test_endpoint_responde_202_cuando_publica(cliente_asincrono):
    cliente, metricas = cliente_asincrono
    pub = PublicadorEnMemoria()
    app.dependency_overrides[obtener_publicador] = lambda: pub

    r = cliente.post(RUTA, json=evento_vuelo())

    assert r.status_code == 202
    cuerpo = r.json()
    assert cuerpo["estado"] == "ENCOLADO"
    assert cuerpo["message_id"] == "mem-1"
    assert len(pub.mensajes) == 1
    # Se contó el evento recibido en la ingesta.
    assert "EventosRecibidos" in metricas.contados


def test_endpoint_responde_503_cuando_el_publicador_falla(cliente_asincrono):
    cliente, _ = cliente_asincrono
    app.dependency_overrides[obtener_publicador] = lambda: _PublicadorQueFalla()

    r = cliente.post(RUTA, json=evento_vuelo())

    assert r.status_code == 503
    assert r.json()["detail"]["codigo"] == "COLA_NO_DISPONIBLE"


# --- Worker --------------------------------------------------------------------------------


def test_worker_procesa_mensaje_y_crea_siniestro_sin_desembolso(monkeypatch):
    monkeypatch.setenv("EC_ORDENAR_DESEMBOLSO", "false")

    polizas = RepositorioPolizasEnMemoria()
    polizas.guardar(poliza_parametrica())
    siniestros = RepositorioSiniestrosEnMemoria()
    desembolsos_ordenados: list[object] = []

    # Session falsa para que procesar_mensaje no toque la base real.
    class _Sesion:
        def close(self):
            pass

    monkeypatch.setattr(worker_mod, "SessionLocal", lambda: _Sesion())
    monkeypatch.setattr(worker_mod, "RepositorioPolizasPostgres", lambda _db: polizas)
    monkeypatch.setattr(worker_mod, "RepositorioSiniestrosPostgres", lambda _db: siniestros)
    # El reloj del servicio hace que la póliza esté vigente.
    construida = {}

    real_servicio = worker_mod.ServicioTelemetria

    def servicio_con_reloj(*args, **kwargs):
        kwargs["reloj"] = lambda: AHORA
        construida["al_crear"] = kwargs.get("al_crear")
        return real_servicio(*args, **kwargs)

    monkeypatch.setattr(worker_mod, "ServicioTelemetria", servicio_con_reloj)
    # Si algo intentara ordenar desembolso, lo detectaríamos aquí.
    monkeypatch.setattr(
        worker_mod,
        "construir_evaluacion",
        lambda _db: pytest.fail("No debe construir evaluación con desembolso apagado."),
    )

    worker_mod.procesar_mensaje(json.dumps(evento_vuelo()))

    # Con desembolso apagado, al_crear es None: no se ordena desembolso.
    assert construida["al_crear"] is None
    assert desembolsos_ordenados == []
    creado = siniestros.obtener_por_evento("FLIGHT-AV123-20261026-abc")
    assert creado is not None
    assert creado.origen.value == "AUTOMATICO"
    # Siniestro sin evaluar: no hay monto aprobado ni evaluador (no se ejecutó pago).
    assert creado.monto_aprobado is None
    assert creado.evaluado_por is None


def test_worker_idempotente_mismo_evento_un_solo_siniestro(monkeypatch):
    monkeypatch.setenv("EC_ORDENAR_DESEMBOLSO", "false")

    polizas = RepositorioPolizasEnMemoria()
    polizas.guardar(poliza_parametrica())
    siniestros = RepositorioSiniestrosEnMemoria()

    class _Sesion:
        def close(self):
            pass

    real_servicio = worker_mod.ServicioTelemetria

    def servicio_con_reloj(*args, **kwargs):
        kwargs["reloj"] = lambda: AHORA
        return real_servicio(*args, **kwargs)

    monkeypatch.setattr(worker_mod, "SessionLocal", lambda: _Sesion())
    monkeypatch.setattr(worker_mod, "RepositorioPolizasPostgres", lambda _db: polizas)
    monkeypatch.setattr(worker_mod, "RepositorioSiniestrosPostgres", lambda _db: siniestros)
    monkeypatch.setattr(worker_mod, "ServicioTelemetria", servicio_con_reloj)

    worker_mod.procesar_mensaje(json.dumps(evento_vuelo()))
    worker_mod.procesar_mensaje(json.dumps(evento_vuelo()))

    assert len(siniestros.listar_por_cliente("CLI-001")) == 1
