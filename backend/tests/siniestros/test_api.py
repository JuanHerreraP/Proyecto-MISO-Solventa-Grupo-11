"""Pruebas del registro manual de siniestros (HU20)."""

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.seguridad import get_current_user
from app.api.siniestros import obtener_servicio
from app.identidad.modelos import Rol
from app.main import app
from app.polizas.dominio.modelos import EstadoRegistroPoliza
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from app.siniestros.repositorio import RepositorioSiniestrosEnMemoria
from app.siniestros.servicio import ServicioSiniestros
from tests.billetera.fabrica import poliza

RUTA = "/api/v1/siniestros"
# 2026-10-21 10:00 en Bogotá (la póliza de la fábrica va del 2026-10-01 al 2026-12-31).
AHORA = datetime(2026, 10, 21, 15, 0, tzinfo=UTC)
CLIENTE = SimpleNamespace(id="CLI-001", email="ana@gmail.com", rol=Rol.CLIENTE.value)


@pytest.fixture
def entorno():
    polizas = RepositorioPolizasEnMemoria()
    polizas.guardar(poliza())
    siniestros = RepositorioSiniestrosEnMemoria()
    servicio = ServicioSiniestros(siniestros, polizas, reloj=lambda: AHORA)
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    app.dependency_overrides[get_current_user] = lambda: CLIENTE
    yield TestClient(app), polizas, siniestros
    app.dependency_overrides.clear()


def cuerpo(**cambios) -> dict:
    datos = {
        "poliza_id": "POL-1",
        "fecha_evento": "2026-10-20",
        "hora_evento": "18:30:00",
        "lugar": "Aeropuerto El Dorado",
        "descripcion": "El vuelo fue cancelado y hubo gastos adicionales.",
        "estimacion_danos": 850000,
    }
    datos.update(cambios)
    return datos


def test_registro_exitoso_fija_origen_estado_y_cliente(entorno) -> None:
    cliente, _, siniestros = entorno

    r = cliente.post(RUTA, json=cuerpo())

    assert r.status_code == 201
    cuerpo_r = r.json()
    assert cuerpo_r["origen"] == "MANUAL"
    assert cuerpo_r["estado"] == "REGISTRADO"
    assert cuerpo_r["cliente_id"] == "CLI-001"
    assert cuerpo_r["poliza_id"] == "POL-1"
    assert cuerpo_r["moneda"] == "COP"
    assert cuerpo_r["siniestro_id"].startswith("SIN-")
    # El cliente registra para sí mismo: cliente_id == registrado_por.
    assert cuerpo_r["registrado_por"] == "CLI-001"
    assert siniestros.listar_por_cliente("CLI-001")[0].siniestro_id == cuerpo_r["siniestro_id"]


def test_poliza_inexistente_responde_404(entorno) -> None:
    cliente, _, _ = entorno
    r = cliente.post(RUTA, json=cuerpo(poliza_id="POL-404"))
    assert r.status_code == 404
    assert r.json()["detail"]["codigo"] == "POLIZA_NO_ENCONTRADA"


def test_poliza_ajena_responde_403(entorno) -> None:
    cliente, polizas, _ = entorno
    polizas.guardar(poliza(poliza_id="POL-2", cliente_id="OTRO", numero_poliza="SOL-VI-000002"))
    r = cliente.post(RUTA, json=cuerpo(poliza_id="POL-2"))
    assert r.status_code == 403
    assert r.json()["detail"]["codigo"] == "POLIZA_AJENA"


def test_poliza_vencida_responde_409(entorno) -> None:
    cliente, polizas, _ = entorno
    polizas.guardar(poliza(fecha_inicio=date(2024, 1, 1), fecha_fin=date(2024, 12, 31)))
    r = cliente.post(RUTA, json=cuerpo(fecha_evento="2024-06-01"))
    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "POLIZA_NO_VIGENTE"


def test_poliza_cancelada_responde_409(entorno) -> None:
    cliente, polizas, _ = entorno
    polizas.guardar(poliza(estado=EstadoRegistroPoliza.CANCELADA))
    r = cliente.post(RUTA, json=cuerpo())
    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "POLIZA_NO_VIGENTE"


def test_evento_antes_del_inicio_responde_422(entorno) -> None:
    cliente, _, _ = entorno
    r = cliente.post(RUTA, json=cuerpo(fecha_evento="2026-09-15"))
    assert r.status_code == 422
    assert r.json()["detail"]["codigo"] == "FECHA_FUERA_DE_VIGENCIA"


def test_evento_posterior_al_fin_con_poliza_vencida_responde_409(entorno) -> None:
    cliente, polizas, _ = entorno
    # Si el evento es posterior al fin de la póliza, esta ya venció respecto a hoy, así que
    # la vigencia se rechaza primero con 409 (la póliza no está vigente).
    polizas.guardar(poliza(fecha_inicio=date(2026, 9, 1), fecha_fin=date(2026, 10, 10)))
    r = cliente.post(RUTA, json=cuerpo(fecha_evento="2026-10-15"))
    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "POLIZA_NO_VIGENTE"


def test_evento_futuro_responde_422(entorno) -> None:
    cliente, _, _ = entorno
    r = cliente.post(RUTA, json=cuerpo(fecha_evento="2026-10-31"))
    assert r.status_code == 422
    assert r.json()["detail"]["codigo"] == "FECHA_FUTURA"


def test_descripcion_vacia_responde_422(entorno) -> None:
    cliente, _, _ = entorno
    r = cliente.post(RUTA, json=cuerpo(descripcion=""))
    assert r.status_code == 422


def test_descripcion_muy_corta_responde_422(entorno) -> None:
    cliente, _, _ = entorno
    r = cliente.post(RUTA, json=cuerpo(descripcion="corta"))
    assert r.status_code == 422


def test_lugar_vacio_responde_422(entorno) -> None:
    cliente, _, _ = entorno
    r = cliente.post(RUTA, json=cuerpo(lugar=""))
    assert r.status_code == 422


def test_estimacion_negativa_responde_422(entorno) -> None:
    cliente, _, _ = entorno
    r = cliente.post(RUTA, json=cuerpo(estimacion_danos=-1))
    assert r.status_code == 422


def test_sin_autenticacion_responde_401() -> None:
    # Sin override de get_current_user, el token es obligatorio.
    app.dependency_overrides.clear()
    r = TestClient(app).post(RUTA, json=cuerpo())
    assert r.status_code == 401


def test_rol_no_cliente_responde_403(entorno) -> None:
    cliente, _, _ = entorno
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="ASE-1", email="asesor@solventa.com", rol=Rol.ASESOR_VENTAS.value
    )
    r = cliente.post(RUTA, json=cuerpo())
    assert r.status_code == 403
    assert r.json()["detail"]["codigo"] == "ACCESS_DENIED"


def test_listar_devuelve_solo_los_del_cliente(entorno) -> None:
    cliente, polizas, _ = entorno
    # Un siniestro propio recién registrado.
    creado = cliente.post(RUTA, json=cuerpo()).json()

    r = cliente.get(RUTA)

    assert r.status_code == 200
    lista = r.json()
    assert [s["siniestro_id"] for s in lista] == [creado["siniestro_id"]]
    assert lista[0]["cliente_id"] == "CLI-001"


def test_listar_vacio_cuando_no_hay_siniestros(entorno) -> None:
    cliente, _, _ = entorno
    r = cliente.get(RUTA)
    assert r.status_code == 200
    assert r.json() == []
