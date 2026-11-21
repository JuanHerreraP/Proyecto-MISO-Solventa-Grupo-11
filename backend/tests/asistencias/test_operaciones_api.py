"""Pruebas de la API de seguimiento operativo de asistencias (HU06 ampliación)."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.asistencias import obtener_servicio
from app.api.operaciones_asistencias import obtener_polizas
from app.api.seguridad import get_current_user
from app.asistencias.repositorio import (
    RepositorioAsistenciasEnMemoria,
    RepositorioPrestadoresEnMemoria,
)
from app.asistencias.servicio import ServicioAsistencias
from app.identidad.modelos import Rol
from app.main import app
from app.polizas.dominio.modelos import RamoPoliza
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from tests.asistencias.fabrica import BOGOTA, prestador
from tests.billetera.fabrica import poliza

AHORA = datetime(2026, 10, 21, 15, 0, tzinfo=UTC)
CLIENTE = SimpleNamespace(id="CLI-001", email="ana@gmail.com", rol=Rol.CLIENTE.value)
OPERACIONES = SimpleNamespace(
    id="OPS-1", email="ops@solventa.com", rol=Rol.OPERACIONES_SINIESTROS.value
)
RUTA_CLI = "/api/v1/asistencias"
RUTA_OPS = "/api/v1/operaciones/asistencias"
DISPOSITIVOS = dict(ramo=RamoPoliza.PROTECCION_DISPOSITIVOS)


@pytest.fixture
def entorno():
    polizas = RepositorioPolizasEnMemoria()
    polizas.guardar(poliza(**DISPOSITIVOS))
    prestadores = RepositorioPrestadoresEnMemoria()
    prestadores.guardar(prestador(prestador_id="PREST-TEC-001", latitud=4.7150, longitud=-74.0690))
    asistencias = RepositorioAsistenciasEnMemoria()
    servicio = ServicioAsistencias(
        prestadores=prestadores,
        asistencias=asistencias,
        polizas=polizas,
        reloj=lambda: AHORA,
    )
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    app.dependency_overrides[obtener_polizas] = lambda: polizas
    app.dependency_overrides[get_current_user] = lambda: CLIENTE
    yield TestClient(app), servicio
    app.dependency_overrides.clear()


def _como(usuario) -> None:
    app.dependency_overrides[get_current_user] = lambda: usuario


def _crear_asistencia(cliente: TestClient) -> str:
    _como(CLIENTE)
    cuerpo = {
        "poliza_id": "POL-1",
        "prestador_id": "PREST-TEC-001",
        "servicio": "REPARACION_DISPOSITIVO",
        "latitud": BOGOTA[0],
        "longitud": BOGOTA[1],
        "observaciones": "El dispositivo no enciende.",
    }
    return cliente.post(RUTA_CLI, json=cuerpo).json()["asistencia_id"]


# --- seguridad por rol ------------------------------------------------------------------


def test_operaciones_lista_sin_rol_operativo_403(entorno):
    cliente, _ = entorno
    _como(CLIENTE)  # el cliente no puede acceder a la bandeja operativa
    r = cliente.get(RUTA_OPS)
    assert r.status_code == 403


def test_operaciones_sin_token_401(entorno):
    cliente, _ = entorno
    app.dependency_overrides.pop(get_current_user, None)
    r = TestClient(app).get(RUTA_OPS)
    assert r.status_code == 401


def test_cliente_no_puede_aceptar_403(entorno):
    cliente, _ = entorno
    asi = _crear_asistencia(cliente)
    _como(CLIENTE)
    r = cliente.post(f"{RUTA_OPS}/{asi}/aceptacion", json={})
    assert r.status_code == 403


def test_cliente_no_puede_modificar_eta_403(entorno):
    cliente, _ = entorno
    asi = _crear_asistencia(cliente)
    _como(CLIENTE)
    r = cliente.patch(f"{RUTA_OPS}/{asi}/seguimiento", json={"tiempo_estimado_llegada_minutos": 10})
    assert r.status_code == 403


def test_otro_rol_no_operativo_403(entorno):
    cliente, _ = entorno
    asi = _crear_asistencia(cliente)
    _como(SimpleNamespace(id="ASE-1", email="a@x.com", rol=Rol.ASESOR_VENTAS.value))
    assert cliente.get(RUTA_OPS).status_code == 403
    assert cliente.get(f"{RUTA_OPS}/{asi}").status_code == 403


# --- consulta operativa -----------------------------------------------------------------


def test_operaciones_lista_y_detalle(entorno):
    cliente, _ = entorno
    asi = _crear_asistencia(cliente)
    _como(OPERACIONES)

    lista = cliente.get(RUTA_OPS)
    assert lista.status_code == 200
    assert [a["asistencia_id"] for a in lista.json()] == [asi]
    assert lista.json()[0]["cliente_id"] == "CLI-001"
    assert lista.headers["Cache-Control"] == "no-store"

    detalle = cliente.get(f"{RUTA_OPS}/{asi}")
    assert detalle.status_code == 200
    cuerpo = detalle.json()
    assert cuerpo["estado"] == "SOLICITADA"
    assert cuerpo["numero_poliza"] == "SOL-VI-000001"
    assert cuerpo["aceptada_en"] is None
    assert cuerpo["tiempo_estimado_llegada_minutos"] is None


def test_operaciones_detalle_inexistente_404(entorno):
    cliente, _ = entorno
    _como(OPERACIONES)
    assert cliente.get(f"{RUTA_OPS}/ASI-NO").status_code == 404


def test_operaciones_filtra_por_estado(entorno):
    cliente, _ = entorno
    asi = _crear_asistencia(cliente)
    _como(OPERACIONES)
    cliente.post(f"{RUTA_OPS}/{asi}/aceptacion", json={})
    assert [
        a["asistencia_id"] for a in cliente.get(RUTA_OPS, params={"estado": "ACEPTADA"}).json()
    ] == [asi]
    assert cliente.get(RUTA_OPS, params={"estado": "SOLICITADA"}).json() == []


# --- aceptación -------------------------------------------------------------------------


def test_aceptar_sin_eta_pasa_a_aceptada(entorno):
    cliente, _ = entorno
    asi = _crear_asistencia(cliente)
    _como(OPERACIONES)
    r = cliente.post(f"{RUTA_OPS}/{asi}/aceptacion", json={})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["estado"] == "ACEPTADA"
    assert cuerpo["aceptada_en"] is not None
    assert cuerpo["tiempo_estimado_llegada_minutos"] is None


def test_aceptar_con_eta(entorno):
    cliente, _ = entorno
    asi = _crear_asistencia(cliente)
    _como(OPERACIONES)
    r = cliente.post(f"{RUTA_OPS}/{asi}/aceptacion", json={"tiempo_estimado_llegada_minutos": 20})
    assert r.status_code == 200
    assert r.json()["estado"] == "ACEPTADA"
    assert r.json()["tiempo_estimado_llegada_minutos"] == 20


def test_aceptar_dos_veces_409(entorno):
    cliente, _ = entorno
    asi = _crear_asistencia(cliente)
    _como(OPERACIONES)
    cliente.post(f"{RUTA_OPS}/{asi}/aceptacion", json={})
    r = cliente.post(f"{RUTA_OPS}/{asi}/aceptacion", json={})
    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "ASISTENCIA_YA_ACEPTADA"


def test_aceptar_cancelada_409(entorno):
    cliente, _ = entorno
    asi = _crear_asistencia(cliente)
    _como(CLIENTE)
    cliente.post(f"{RUTA_CLI}/{asi}/cancelacion")
    _como(OPERACIONES)
    r = cliente.post(f"{RUTA_OPS}/{asi}/aceptacion", json={})
    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "ASISTENCIA_CANCELADA"


def test_aceptar_inexistente_404(entorno):
    cliente, _ = entorno
    _como(OPERACIONES)
    assert cliente.post(f"{RUTA_OPS}/ASI-NO/aceptacion", json={}).status_code == 404


def test_aceptar_eta_fuera_de_rango_422(entorno):
    cliente, _ = entorno
    asi = _crear_asistencia(cliente)
    _como(OPERACIONES)
    assert (
        cliente.post(
            f"{RUTA_OPS}/{asi}/aceptacion", json={"tiempo_estimado_llegada_minutos": 0}
        ).status_code
        == 422
    )
    assert (
        cliente.post(
            f"{RUTA_OPS}/{asi}/aceptacion", json={"tiempo_estimado_llegada_minutos": 5000}
        ).status_code
        == 422
    )


# --- seguimiento (ETA posterior) --------------------------------------------------------


def test_actualizar_eta_despues_de_aceptar(entorno):
    cliente, _ = entorno
    asi = _crear_asistencia(cliente)
    _como(OPERACIONES)
    cliente.post(f"{RUTA_OPS}/{asi}/aceptacion", json={})
    r = cliente.patch(f"{RUTA_OPS}/{asi}/seguimiento", json={"tiempo_estimado_llegada_minutos": 15})
    assert r.status_code == 200
    assert r.json()["estado"] == "ACEPTADA"
    assert r.json()["tiempo_estimado_llegada_minutos"] == 15


def test_actualizar_eta_en_solicitada_409(entorno):
    cliente, _ = entorno
    asi = _crear_asistencia(cliente)
    _como(OPERACIONES)
    r = cliente.patch(f"{RUTA_OPS}/{asi}/seguimiento", json={"tiempo_estimado_llegada_minutos": 15})
    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "TRANSICION_ESTADO_INVALIDA"


# --- el cliente ve el seguimiento -------------------------------------------------------


def test_cliente_ve_estado_y_eta_tras_aceptacion(entorno):
    cliente, _ = entorno
    asi = _crear_asistencia(cliente)
    _como(OPERACIONES)
    cliente.post(f"{RUTA_OPS}/{asi}/aceptacion", json={"tiempo_estimado_llegada_minutos": 20})

    _como(CLIENTE)
    lista = cliente.get(RUTA_CLI).json()
    propia = next(a for a in lista if a["asistencia_id"] == asi)
    assert propia["estado"] == "ACEPTADA"
    assert propia["aceptada_en"] is not None
    assert propia["tiempo_estimado_llegada_minutos"] == 20


def test_cliente_ve_aceptada_sin_eta(entorno):
    cliente, _ = entorno
    asi = _crear_asistencia(cliente)
    _como(OPERACIONES)
    cliente.post(f"{RUTA_OPS}/{asi}/aceptacion", json={})

    _como(CLIENTE)
    propia = next(a for a in cliente.get(RUTA_CLI).json() if a["asistencia_id"] == asi)
    assert propia["estado"] == "ACEPTADA"
    assert propia["tiempo_estimado_llegada_minutos"] is None
