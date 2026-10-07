import statistics
import time

import pytest
from fastapi.testclient import TestClient

from app.api.perfilamiento import obtener_servicio
from app.main import app
from app.perfilamiento.repositorio import RepositorioPerfilesEnMemoria
from app.perfilamiento.servicio import ServicioPerfilamiento
from tests.perfilamiento.fabrica import senales

RUTA = "/api/v1/perfiles-riesgo"
SERVICIO = {"X-Rol": "SERVICIO_INTERNO"}
ANALISTA = {"X-Rol": "ANALISTA_RIESGOS"}
CLIENTE = {"X-Rol": "CLIENTE"}


@pytest.fixture
def cliente():
    servicio = ServicioPerfilamiento(RepositorioPerfilesEnMemoria())
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    yield TestClient(app)
    app.dependency_overrides.clear()


def cuerpo(**cambios) -> dict:
    return senales(**cambios).model_dump(mode="json")


def test_genera_el_perfil_y_lo_deja_consultable(cliente):
    creado = cliente.post(RUTA, json=cuerpo(), headers=SERVICIO)

    assert creado.status_code == 201
    assert creado.json()["dictamen"] == "ACEPTADO"
    assert float(creado.headers["X-Tiempo-Proceso-Ms"]) >= 0

    consultado = cliente.get(f"{RUTA}/CLI-001", headers=ANALISTA)
    assert consultado.status_code == 200
    assert consultado.json()["perfil_id"] == creado.json()["perfil_id"]
    assert consultado.json()["reglas_aplicadas"]


def test_el_analista_ve_los_elementos_para_explicar_la_decision(cliente):
    cliente.post(RUTA, json=cuerpo(nivel_endeudamiento=0.95), headers=SERVICIO)

    perfil = cliente.get(f"{RUTA}/CLI-001", headers=ANALISTA).json()

    assert perfil["dictamen"] == "RECHAZADO"
    assert perfil["puntaje_riesgo"] is not None
    assert [r["codigo"] for r in perfil["reglas_aplicadas"]] == [
        "SCORING",
        "RECHAZO_ENDEUDAMIENTO",
    ]


def test_el_cliente_solo_recibe_la_oferta_y_su_explicacion(cliente):
    cliente.post(RUTA, json=cuerpo(), headers=SERVICIO)

    oferta = cliente.get(f"{RUTA}/CLI-001/oferta", headers=CLIENTE)

    assert oferta.status_code == 200
    assert "puntaje_riesgo" not in oferta.json()
    assert "reglas_aplicadas" not in oferta.json()
    assert oferta.json()["explicacion"]


def test_el_cliente_no_puede_ver_el_detalle_del_perfil(cliente):
    cliente.post(RUTA, json=cuerpo(), headers=SERVICIO)

    assert cliente.get(f"{RUTA}/CLI-001", headers=CLIENTE).status_code == 403


def test_el_cliente_no_puede_generar_perfiles(cliente):
    assert cliente.post(RUTA, json=cuerpo(), headers=CLIENTE).status_code == 403


def test_sin_identificar_al_solicitante_se_rechaza(cliente):
    assert cliente.post(RUTA, json=cuerpo()).status_code == 401
    assert cliente.get(f"{RUTA}/CLI-001").status_code == 401


def test_rol_desconocido_se_rechaza(cliente):
    assert cliente.get(f"{RUTA}/CLI-001", headers={"X-Rol": "ADMIN"}).status_code == 403


def test_consentimiento_no_vigente_devuelve_conflicto(cliente):
    respuesta = cliente.post(RUTA, json=cuerpo(consentimiento_vigente=False), headers=SERVICIO)

    assert respuesta.status_code == 409


def test_entrada_incompleta_se_rechaza(cliente):
    incompleto = cuerpo()
    del incompleto["open_data"]

    assert cliente.post(RUTA, json=incompleto, headers=SERVICIO).status_code == 422


def test_senal_fuera_de_rango_se_rechaza(cliente):
    invalido = cuerpo()
    invalido["open_finance"]["comportamiento_pago"] = 1.4

    assert cliente.post(RUTA, json=invalido, headers=SERVICIO).status_code == 422


def test_campo_no_previsto_en_el_contrato_se_rechaza(cliente):
    extra = cuerpo()
    extra["open_finance"]["score_del_proveedor_x"] = 0.7

    assert cliente.post(RUTA, json=extra, headers=SERVICIO).status_code == 422


def test_perfil_inexistente_devuelve_no_encontrado(cliente):
    assert cliente.get(f"{RUTA}/NO-EXISTE", headers=ANALISTA).status_code == 404
    assert cliente.get(f"{RUTA}/NO-EXISTE/oferta", headers=CLIENTE).status_code == 404


def test_humo_de_latencia_del_calculo_frente_a_ec02(cliente):
    """Humo local: mide solo el cálculo en proceso, sin red ni fuentes externas.

    No valida EC02. La evidencia de EC02 sale de `tests/k6/perfil_riesgo.js` contra el
    servicio desplegado.
    """
    tiempos = []
    for i in range(200):
        inicio = time.perf_counter()
        respuesta = cliente.post(RUTA, json=cuerpo(cliente_id=f"CLI-{i}"), headers=SERVICIO)
        tiempos.append((time.perf_counter() - inicio) * 1000)
        assert respuesta.status_code == 201

    percentiles = statistics.quantiles(tiempos, n=100)
    assert percentiles[94] <= 400
    assert percentiles[98] <= 800
