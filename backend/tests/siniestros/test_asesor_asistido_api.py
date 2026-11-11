"""Pruebas del registro de siniestros asistido por un asesor de ventas (HU20)."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.seguridad import get_current_user
from app.api.siniestros import obtener_asociaciones, obtener_servicio
from app.identidad.asociacion import RepositorioAsesorClienteEnMemoria
from app.identidad.modelos import Rol
from app.main import app
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from app.siniestros.repositorio import RepositorioSiniestrosEnMemoria
from app.siniestros.servicio import ServicioSiniestros
from tests.billetera.fabrica import poliza

RUTA = "/api/v1/siniestros"
RUTA_ASISTIDO = "/api/v1/siniestros/asistido"
AHORA = datetime(2026, 10, 21, 15, 0, tzinfo=UTC)
ASESOR = SimpleNamespace(id="ASE-1", email="asesor@solventa.com", rol=Rol.ASESOR_VENTAS.value)


@pytest.fixture
def entorno():
    polizas = RepositorioPolizasEnMemoria()
    # Póliza del cliente CLI-001 (coincide con la fábrica).
    polizas.guardar(poliza())
    siniestros = RepositorioSiniestrosEnMemoria()
    servicio = ServicioSiniestros(siniestros, polizas, reloj=lambda: AHORA)
    asociaciones = RepositorioAsesorClienteEnMemoria()

    app.dependency_overrides[obtener_servicio] = lambda: servicio
    app.dependency_overrides[obtener_asociaciones] = lambda: asociaciones
    app.dependency_overrides[get_current_user] = lambda: ASESOR
    yield TestClient(app), polizas, siniestros, asociaciones
    app.dependency_overrides.clear()


def cuerpo(**cambios) -> dict:
    datos = {
        "cliente_id": "CLI-001",
        "poliza_id": "POL-1",
        "fecha_evento": "2026-10-20",
        "hora_evento": "18:30:00",
        "lugar": "Aeropuerto El Dorado",
        "descripcion": "El vuelo fue cancelado y hubo gastos adicionales.",
        "estimacion_danos": 850000,
    }
    datos.update(cambios)
    return datos


def test_asesor_asociado_registra_en_nombre_del_cliente(entorno) -> None:
    cliente, _, siniestros, asociaciones = entorno
    asociaciones.asociar("ASE-1", "CLI-001")

    r = cliente.post(RUTA_ASISTIDO, json=cuerpo())

    assert r.status_code == 201
    cuerpo_r = r.json()
    assert cuerpo_r["cliente_id"] == "CLI-001"
    # El asesor queda registrado como quien lo creó.
    assert cuerpo_r["registrado_por"] == "ASE-1"
    assert cuerpo_r["origen"] == "MANUAL"
    assert siniestros.listar_por_cliente("CLI-001")[0].siniestro_id == cuerpo_r["siniestro_id"]


def test_asesor_sin_asociacion_recibe_403(entorno) -> None:
    cliente, _, _, _ = entorno
    r = cliente.post(RUTA_ASISTIDO, json=cuerpo())
    assert r.status_code == 403
    assert r.json()["detail"]["codigo"] == "CLIENTE_NO_ASOCIADO"


def test_asesor_poliza_de_otro_cliente_responde_403(entorno) -> None:
    cliente, polizas, _, asociaciones = entorno
    asociaciones.asociar("ASE-1", "CLI-001")
    # Póliza que pertenece a otro cliente, no a CLI-001.
    polizas.guardar(poliza(poliza_id="POL-9", cliente_id="OTRO", numero_poliza="SOL-VI-000009"))
    r = cliente.post(RUTA_ASISTIDO, json=cuerpo(poliza_id="POL-9"))
    assert r.status_code == 403
    assert r.json()["detail"]["codigo"] == "POLIZA_AJENA"


def test_cliente_no_puede_usar_endpoint_asistido(entorno) -> None:
    cliente, _, _, _ = entorno
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="CLI-001", email="ana@gmail.com", rol=Rol.CLIENTE.value
    )
    r = cliente.post(RUTA_ASISTIDO, json=cuerpo())
    assert r.status_code == 403
    assert r.json()["detail"]["codigo"] == "ACCESS_DENIED"


def test_asesor_lista_siniestros_de_cliente_asociado(entorno) -> None:
    cliente, _, _, asociaciones = entorno
    asociaciones.asociar("ASE-1", "CLI-001")
    creado = cliente.post(RUTA_ASISTIDO, json=cuerpo()).json()

    r = cliente.get(RUTA, params={"cliente_id": "CLI-001"})

    assert r.status_code == 200
    assert [s["siniestro_id"] for s in r.json()] == [creado["siniestro_id"]]


def test_asesor_lista_sin_cliente_responde_422(entorno) -> None:
    cliente, _, _, _ = entorno
    r = cliente.get(RUTA)
    assert r.status_code == 422
    assert r.json()["detail"]["codigo"] == "CLIENTE_REQUERIDO"


def test_asesor_lista_cliente_no_asociado_responde_403(entorno) -> None:
    cliente, _, _, _ = entorno
    r = cliente.get(RUTA, params={"cliente_id": "CLI-999"})
    assert r.status_code == 403
    assert r.json()["detail"]["codigo"] == "CLIENTE_NO_ASOCIADO"
