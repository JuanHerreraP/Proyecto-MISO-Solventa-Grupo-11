"""API de primas pendientes: acceso, formato y encabezados (HU21)."""

import pytest
from fastapi.testclient import TestClient

from app.api.cotizaciones import ActorCotizacion, TipoActorCotizacion, actor_actual
from app.api.primas_pendientes import obtener_servicio
from app.identidad.modelos import Rol
from app.main import app
from tests.primas_pendientes.fabrica import (
    CLIENTE,
    EntornoPrimas,
    cotizacion_vigente,
    crear_entorno_primas,
)

RUTA = "/api/v1/primas-pendientes"


def actor(rol=Rol.CLIENTE, actor_id=CLIENTE, tipo=TipoActorCotizacion.USUARIO):
    return lambda: ActorCotizacion(tipo=tipo, actor_id=actor_id, rol=rol)


def con_entorno(e: EntornoPrimas, **actor_args) -> TestClient:
    app.dependency_overrides[obtener_servicio] = lambda: e.servicio
    app.dependency_overrides[actor_actual] = actor(**actor_args)
    return TestClient(app)


@pytest.fixture
def entorno():
    e = crear_entorno_primas()
    yield con_entorno(e), e
    app.dependency_overrides.clear()


def test_lista_vacia_cuando_no_hay_nada_pendiente(entorno) -> None:
    cliente, _ = entorno

    respuesta = cliente.get(RUTA)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"primas": [], "total": 0}


def test_lista_la_renovacion_y_la_cotizacion_con_el_formato_de_la_app(entorno) -> None:
    cliente, e = entorno
    renovacion = e.iniciar_renovacion()
    e.base.cotizaciones.guardar(cotizacion_vigente(vigente_dias=9))

    respuesta = cliente.get(RUTA)

    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert cuerpo["total"] == 2
    primera, segunda = cuerpo["primas"]
    assert primera["tipo"] == "RENOVACION" and primera["accion"] == "PAGAR"
    assert primera["referencia_id"] == renovacion.renovacion_id
    assert primera["cotizacion_id"] == renovacion.cotizacion_id
    assert primera["numero_poliza"] == "SOL-2026-VIDA0001"
    assert primera["monto"] == "420000.00" and primera["moneda"] == "COP"
    assert primera["fecha_limite"] is not None
    assert segunda["tipo"] == "COTIZACION" and segunda["poliza_id"] is None
    assert segunda["cotizacion_id"] == "COT-NUEVA" and segunda["monto"] == "89000.00"


def test_un_rol_que_no_es_cliente_recibe_403(entorno) -> None:
    cliente, _ = entorno
    app.dependency_overrides[actor_actual] = actor(rol=Rol.ASESOR_VENTAS, actor_id="ASE-1")

    assert cliente.get(RUTA).status_code == 403


def test_un_actor_que_no_es_usuario_recibe_403(entorno) -> None:
    cliente, _ = entorno
    app.dependency_overrides[actor_actual] = actor(tipo=TipoActorCotizacion.SOCIO)

    assert cliente.get(RUTA).status_code == 403


def test_cada_cliente_ve_solo_lo_suyo(entorno) -> None:
    cliente, e = entorno
    e.base.cotizaciones.guardar(cotizacion_vigente("COT-AJENA", cliente_id="CLI-OTRO"))
    app.dependency_overrides[actor_actual] = actor(actor_id="CLI-OTRO")

    cuerpo = cliente.get(RUTA).json()

    assert [p["cotizacion_id"] for p in cuerpo["primas"]] == ["COT-AJENA"]
