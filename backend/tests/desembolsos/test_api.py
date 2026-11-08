"""API de desembolsos: cuenta del cliente, bandeja y decisiones de Operaciones (HU15)."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.desembolsos import obtener_desembolsos, obtener_evaluacion
from app.api.seguridad import get_current_user
from app.identidad.modelos import Rol
from app.main import app
from tests.desembolsos.fabrica import CLIENTE, OPERADOR, crear_entorno, siniestro

CUENTA = "/api/v1/desembolsos/cuenta"
BANDEJA = "/api/v1/operaciones/siniestros"


def usuario(rol: Rol, usuario_id: str):
    return lambda: SimpleNamespace(id=usuario_id, rol=rol.value, email="x@example.com")


@pytest.fixture
def entorno():
    e = crear_entorno(siniestro(), siniestro(siniestro_id="SIN-2", cliente_id="CLI-002"))
    app.dependency_overrides[obtener_desembolsos] = lambda: e.desembolsos
    app.dependency_overrides[obtener_evaluacion] = lambda: e.evaluacion
    app.dependency_overrides[get_current_user] = usuario(Rol.CLIENTE, CLIENTE)
    yield TestClient(app), e
    app.dependency_overrides.clear()


def como(rol: Rol, usuario_id: str) -> None:
    app.dependency_overrides[get_current_user] = usuario(rol, usuario_id)


def test_el_cliente_registra_su_cuenta_y_solo_ve_los_ultimos_digitos(entorno) -> None:
    cliente, _ = entorno

    assert cliente.get(CUENTA).json() is None
    respuesta = cliente.put(
        CUENTA,
        json={"codigo_banco": "1007", "tipo_cuenta": "AHORROS", "numero_cuenta": "4567891234"},
    )

    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert cuerpo["nombre_banco"] == "Bancolombia"
    assert cuerpo["ultimos_digitos"] == "1234"
    assert "4567891234" not in respuesta.text
    assert "token" not in respuesta.text
    assert cliente.get(CUENTA).json()["ultimos_digitos"] == "1234"


def test_una_cuenta_invalida_se_rechaza(entorno) -> None:
    cliente, _ = entorno

    respuesta = cliente.put(
        CUENTA, json={"codigo_banco": "0000", "tipo_cuenta": "AHORROS", "numero_cuenta": "12"}
    )

    assert respuesta.status_code == 422


def test_operaciones_aprueba_y_el_cliente_ve_su_desembolso(entorno) -> None:
    cliente, _ = entorno
    como(Rol.OPERACIONES_SINIESTROS, OPERADOR)

    bandeja = cliente.get(BANDEJA, params={"estado": "REGISTRADO"}).json()
    aprobado = cliente.post(f"{BANDEJA}/SIN-1/aprobacion", json={})

    assert {s["siniestro_id"] for s in bandeja} == {"SIN-1", "SIN-2"}
    assert aprobado.status_code == 200
    cuerpo = aprobado.json()
    assert cuerpo["estado"] == "APROBADO"
    assert cuerpo["evaluado_por"] == OPERADOR
    assert cuerpo["desembolso"]["estado"] == "COMPLETADA"
    assert cuerpo["desembolso"]["medio"] == "CODIGO_RETIRO"
    # Operaciones no ve el código de retiro: es del titular.
    assert cuerpo["desembolso"]["codigo_retiro"] is None

    como(Rol.CLIENTE, CLIENTE)
    propios = cliente.get("/api/v1/desembolsos").json()
    assert len(propios) == 1
    assert propios[0]["siniestro_id"] == "SIN-1"
    assert len(propios[0]["codigo_retiro"]) == 8
    assert propios[0]["referencia_transaccion"].startswith("RET-")


def test_el_cliente_no_ve_desembolsos_de_otro(entorno) -> None:
    cliente, _ = entorno
    como(Rol.OPERACIONES_SINIESTROS, OPERADOR)
    cliente.post(f"{BANDEJA}/SIN-2/aprobacion", json={})

    como(Rol.CLIENTE, CLIENTE)
    assert cliente.get("/api/v1/desembolsos").json() == []


def test_el_cliente_no_puede_aprobar_ni_ver_la_bandeja(entorno) -> None:
    cliente, e = entorno

    assert cliente.get(BANDEJA).status_code == 403
    assert cliente.post(f"{BANDEJA}/SIN-1/aprobacion", json={}).status_code == 403
    assert cliente.post(f"{BANDEJA}/SIN-1/rechazo", json={"motivo": "No aplica"}).status_code == 403
    assert cliente.post(f"{BANDEJA}/SIN-1/desembolso/reintento").status_code == 403
    assert e.desembolsos.obtener_por_siniestro("SIN-1") is None


def test_operaciones_no_usa_las_rutas_del_cliente(entorno) -> None:
    cliente, _ = entorno
    como(Rol.OPERACIONES_SINIESTROS, OPERADOR)

    assert cliente.get(CUENTA).status_code == 403
    assert cliente.get("/api/v1/desembolsos").status_code == 403


def test_monto_invalido_y_decisiones_en_conflicto(entorno) -> None:
    cliente, _ = entorno
    como(Rol.OPERACIONES_SINIESTROS, OPERADOR)

    excesivo = cliente.post(f"{BANDEJA}/SIN-1/aprobacion", json={"monto_aprobado": "99999999"})
    assert excesivo.status_code == 422
    assert excesivo.json()["detail"]["codigo"] == "MONTO_INVALIDO"

    rechazo = cliente.post(f"{BANDEJA}/SIN-1/rechazo", json={"motivo": "Evento no cubierto"})
    assert rechazo.status_code == 200
    assert rechazo.json()["estado"] == "RECHAZADO"

    conflicto = cliente.post(f"{BANDEJA}/SIN-1/aprobacion", json={})
    assert conflicto.status_code == 409
    assert conflicto.json()["detail"]["codigo"] == "SINIESTRO_YA_EVALUADO"

    assert cliente.post(f"{BANDEJA}/SIN-NADA/aprobacion", json={}).status_code == 404


def test_reintentar_un_desembolso_pendiente(entorno) -> None:
    cliente, e = entorno
    como(Rol.OPERACIONES_SINIESTROS, OPERADOR)
    e.red.caida = True

    aprobado = cliente.post(f"{BANDEJA}/SIN-1/aprobacion", json={}).json()
    assert aprobado["desembolso"]["estado"] == "PENDIENTE"

    e.red.caida = False
    reintento = cliente.post(f"{BANDEJA}/SIN-1/desembolso/reintento")
    assert reintento.status_code == 200
    assert reintento.json()["estado"] == "COMPLETADA"

    otra_vez = cliente.post(f"{BANDEJA}/SIN-1/desembolso/reintento")
    assert otra_vez.status_code == 409
    assert otra_vez.json()["detail"]["codigo"] == "DESEMBOLSO_COMPLETADO"
