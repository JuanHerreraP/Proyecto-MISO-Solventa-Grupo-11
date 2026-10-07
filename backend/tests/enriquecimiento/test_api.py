from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.enriquecimiento import obtener_consentimientos, obtener_servicio
from app.api.perfilamiento import obtener_servicio as obtener_perfilamiento
from app.main import app
from app.perfilamiento.repositorio import RepositorioPerfilesEnMemoria
from app.perfilamiento.servicio import ServicioPerfilamiento
from tests.enriquecimiento.dobles import INICIO, Escenario

ASESOR = {"X-Rol": "ASESOR_VENTAS"}
ANALISTA = {"X-Rol": "ANALISTA_RIESGOS"}
CLIENTE = {"X-Rol": "CLIENTE"}
SOLICITUD = {"cliente_id": "CLI-001", "cotizacion_id": "COT-001"}


@pytest.fixture
def escenario():
    return Escenario()


@pytest.fixture
def api(escenario):
    perfilamiento = ServicioPerfilamiento(RepositorioPerfilesEnMemoria())
    app.dependency_overrides[obtener_servicio] = lambda: escenario.servicio
    app.dependency_overrides[obtener_consentimientos] = lambda: escenario.consentimientos
    app.dependency_overrides[obtener_perfilamiento] = lambda: perfilamiento
    yield TestClient(app)
    app.dependency_overrides.clear()


def consentimiento(dias: int = 30) -> dict:
    return {
        "consentimiento_id": "CONS-001",
        "cliente_id": "CLI-001",
        "vence_en": (INICIO + timedelta(days=dias)).isoformat(),
    }


def test_flujo_completo_consentimiento_enriquecimiento_y_perfil(api):
    assert (
        api.post("/api/v1/consentimientos", json=consentimiento(), headers=CLIENTE).status_code
        == 201
    )

    respuesta = api.post("/api/v1/enriquecimientos", json=SOLICITUD, headers=ASESOR)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["dictamen"] == "ACEPTADO"
    assert cuerpo["enriquecimiento"]["senales"]["origen"] == "FUENTES_EXTERNAS"
    assert len(cuerpo["enriquecimiento"]["fuentes"]) == 2

    perfil = api.get("/api/v1/perfiles-riesgo/CLI-001", headers=ANALISTA)
    assert perfil.status_code == 200
    assert perfil.json()["perfil_id"] == cuerpo["perfil_id"]
    assert perfil.json()["consentimiento_id"] == "CONS-001"


def test_el_analista_consulta_las_senales_consolidadas_y_su_origen(api, escenario):
    escenario.con_consentimiento()
    api.post("/api/v1/enriquecimientos", json=SOLICITUD, headers=ASESOR)

    respuesta = api.get("/api/v1/enriquecimientos/CLI-001", headers=ANALISTA)

    assert respuesta.status_code == 200
    assert {f["tipo"] for f in respuesta.json()["fuentes"]} == {"OPEN_FINANCE", "OPEN_DATA"}
    assert all(f["proveedor"] and f["obtenido_en"] for f in respuesta.json()["fuentes"])


def test_sin_consentimiento_vigente_devuelve_conflicto(api):
    assert api.post("/api/v1/enriquecimientos", json=SOLICITUD, headers=ASESOR).status_code == 409


def test_con_un_proveedor_caido_y_cache_el_recorrido_continua(api, escenario):
    escenario.con_consentimiento()
    api.post("/api/v1/enriquecimientos", json=SOLICITUD, headers=ASESOR)
    escenario.open_finance.falla = "respuesta HTTP 503"

    respuesta = api.post("/api/v1/enriquecimientos", json=SOLICITUD, headers=ASESOR)

    assert respuesta.status_code == 201
    assert respuesta.json()["enriquecimiento"]["senales"]["origen"] == "CACHE"
    perfil = api.get("/api/v1/perfiles-riesgo/CLI-001", headers=ANALISTA).json()
    assert perfil["origen_senales"] == "CACHE"


def test_con_un_proveedor_caido_y_sin_cache_devuelve_no_disponible(api, escenario):
    escenario.con_consentimiento()
    escenario.open_data.falla = "respuesta HTTP 500"

    respuesta = api.post("/api/v1/enriquecimientos", json=SOLICITUD, headers=ASESOR)

    assert respuesta.status_code == 503
    assert "OPEN_DATA" in respuesta.json()["detail"]
    assert api.get("/api/v1/perfiles-riesgo/CLI-001", headers=ANALISTA).status_code == 404


def test_el_cliente_no_puede_iniciar_el_enriquecimiento(api, escenario):
    escenario.con_consentimiento()

    assert api.post("/api/v1/enriquecimientos", json=SOLICITUD, headers=CLIENTE).status_code == 403


def test_el_asesor_no_puede_ver_las_senales_consolidadas(api, escenario):
    escenario.con_consentimiento()
    api.post("/api/v1/enriquecimientos", json=SOLICITUD, headers=ASESOR)

    assert api.get("/api/v1/enriquecimientos/CLI-001", headers=ASESOR).status_code == 403


def test_el_analista_no_puede_registrar_consentimientos(api):
    respuesta = api.post("/api/v1/consentimientos", json=consentimiento(), headers=ANALISTA)

    assert respuesta.status_code == 403


def test_sin_identificar_al_solicitante_se_rechaza(api):
    assert api.post("/api/v1/enriquecimientos", json=SOLICITUD).status_code == 401
    assert api.get("/api/v1/enriquecimientos/CLI-001").status_code == 401


def test_solicitud_sin_proceso_de_cotizacion_se_rechaza(api):
    respuesta = api.post("/api/v1/enriquecimientos", json={"cliente_id": "CLI-001"}, headers=ASESOR)

    assert respuesta.status_code == 422


def test_senales_inexistentes_devuelven_no_encontrado(api):
    assert api.get("/api/v1/enriquecimientos/NO-EXISTE", headers=ANALISTA).status_code == 404


def test_con_la_configuracion_por_defecto_el_flujo_corre_con_simuladores():
    """Sin sobrescribir dependencias: lo que arranca con `uvicorn app.main:app` en local."""
    obtener_servicio.cache_clear()
    obtener_consentimientos.cache_clear()
    obtener_perfilamiento.cache_clear()
    api = TestClient(app)
    vigente = {
        "consentimiento_id": "CONS-SIM",
        "cliente_id": "CLI-SIM",
        "vence_en": "2999-01-01T00:00:00Z",
    }
    api.post("/api/v1/consentimientos", json=vigente, headers=CLIENTE)

    respuesta = api.post(
        "/api/v1/enriquecimientos",
        json={"cliente_id": "CLI-SIM", "cotizacion_id": "COT-SIM"},
        headers=ASESOR,
    )

    assert respuesta.status_code == 201
    proveedores = [f["proveedor"] for f in respuesta.json()["enriquecimiento"]["fuentes"]]
    assert proveedores == ["simulador-open-finance", "simulador-open-data"]
