"""Endpoint interno del job de vencimientos y composición del servicio."""

import logging
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.notificaciones import obtener_vencimientos
from app.infraestructura.database import Base
from app.main import app
from app.notificaciones import composicion
from app.notificaciones.canal import EnviadorPushSimulado
from app.notificaciones.servicio import ServicioNotificaciones
from app.notificaciones.vencimientos import ServicioVencimientos
from app.polizas.dominio.modelos import RamoPoliza
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from tests.billetera.fabrica import poliza
from tests.notificaciones.fabrica import CLIENTE, HOY, crear_servicio, dispositivo

RUTA = "/api/v1/internos/notificaciones/vencimientos"
CLAVE = "clave-del-job-de-pruebas"


@pytest.fixture
def job(monkeypatch):
    monkeypatch.setenv("NOTIFICACIONES_CLAVE_INTERNA", CLAVE)
    polizas = RepositorioPolizasEnMemoria()
    polizas.guardar(
        poliza(
            poliza_id="POL-1",
            numero_poliza="SOL-VD-000001",
            ramo=RamoPoliza.VIDA,
            fecha_fin=HOY + timedelta(days=15),
        )
    )
    notificaciones, repos, reloj = crear_servicio(enviador=EnviadorPushSimulado())
    repos.dispositivos.guardar(dispositivo("token-1", cliente_id=CLIENTE))
    servicio = ServicioVencimientos(polizas, notificaciones, reloj=reloj)
    app.dependency_overrides[obtener_vencimientos] = lambda: servicio
    yield TestClient(app), repos
    app.dependency_overrides.clear()


def llamar(cliente, clave=CLAVE, **parametros):
    encabezados = {"X-Clave-Interna": clave} if clave is not None else {}
    return cliente.post(RUTA, headers=encabezados, params=parametros)


def test_el_job_responde_el_resumen_de_lo_avisado(job) -> None:
    cliente, repos = job

    respuesta = llamar(cliente)

    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert cuerpo["fecha"] == HOY.isoformat()
    por_dias = {a["dias"]: a for a in cuerpo["avisos"]}
    assert por_dias[15] == {
        "dias": 15,
        "candidatas": 1,
        "notificadas": 1,
        "repetidas": 0,
        "errores": 0,
    }
    assert por_dias[3]["candidatas"] == 0
    assert len(repos.notificaciones.listar(CLIENTE)) == 1


def test_llamarlo_otra_vez_no_duplica_los_avisos(job) -> None:
    cliente, repos = job
    llamar(cliente)

    segunda = llamar(cliente).json()

    assert segunda["avisos"][0]["repetidas"] == 1
    assert len(repos.notificaciones.listar(CLIENTE)) == 1


def test_acepta_una_fecha_para_recuperar_una_ejecucion_perdida(job) -> None:
    cliente, repos = job

    respuesta = llamar(cliente, fecha=(HOY - timedelta(days=2)).isoformat())

    # Dos días antes la póliza vencía en 17 días: no coincide con ningún aviso.
    assert respuesta.status_code == 200
    assert respuesta.json()["fecha"] == (HOY - timedelta(days=2)).isoformat()
    assert repos.notificaciones.listar(CLIENTE) == []


def test_rechaza_una_fecha_invalida(job) -> None:
    cliente, _ = job

    assert llamar(cliente, fecha="no-es-fecha").status_code == 422


@pytest.mark.parametrize(
    "clave", [None, "", "otra-clave", CLAVE + "x", "clave-ñ-con-acentos".encode()]
)
def test_sin_la_clave_correcta_responde_401_y_no_avisa(job, clave) -> None:
    cliente, repos = job

    respuesta = llamar(cliente, clave=clave)

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"]["codigo"] == "CLAVE_INVALIDA"
    assert repos.notificaciones.listar(CLIENTE) == []


def test_sin_clave_configurada_el_endpoint_esta_apagado(job, monkeypatch) -> None:
    cliente, repos = job
    monkeypatch.delenv("NOTIFICACIONES_CLAVE_INTERNA")

    respuesta = llamar(cliente, clave="cualquiera")

    assert respuesta.status_code == 503
    assert respuesta.json()["detail"]["codigo"] == "JOB_NO_CONFIGURADO"
    assert repos.notificaciones.listar(CLIENTE) == []


def test_el_cableado_real_con_la_base_avisa_de_punta_a_punta(monkeypatch) -> None:
    from app.infraestructura.database import get_db
    from app.polizas.repositorio import RepositorioPolizasPostgres

    monkeypatch.setenv("NOTIFICACIONES_CLAVE_INTERNA", CLAVE)
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sesion = sessionmaker(bind=engine)()
    from datetime import UTC, datetime

    hoy_real = datetime.now(UTC).date()
    RepositorioPolizasPostgres(sesion).guardar(
        poliza(
            poliza_id="POL-1",
            ramo=RamoPoliza.VIDA,
            fecha_inicio=hoy_real - timedelta(days=300),
            fecha_fin=hoy_real + timedelta(days=15),
        )
    )
    app.dependency_overrides[get_db] = lambda: sesion
    try:
        respuesta = llamar(TestClient(app), fecha=hoy_real.isoformat())
    finally:
        app.dependency_overrides.clear()
        sesion.close()
        engine.dispose()

    assert respuesta.status_code == 200
    assert respuesta.json()["avisos"][0]["notificadas"] == 1


# --- Composición ---------------------------------------------------------------------------


@pytest.fixture(autouse=False)
def entorno_limpio(monkeypatch):
    for variable in ("PUSH_PROVEEDOR", "FCM_CREDENCIALES_JSON", "FCM_CREDENCIALES_PATH"):
        monkeypatch.delenv(variable, raising=False)
    composicion.enviador_push.cache_clear()
    yield monkeypatch
    composicion.enviador_push.cache_clear()


def test_el_canal_del_proceso_se_crea_una_vez_y_se_reutiliza(entorno_limpio) -> None:
    primero = composicion.enviador_push()

    assert isinstance(primero, EnviadorPushSimulado)
    assert composicion.enviador_push() is primero


def test_una_configuracion_de_push_invalida_no_tumba_el_flujo_de_negocio(
    entorno_limpio, caplog
) -> None:
    entorno_limpio.setenv("PUSH_PROVEEDOR", "fcm")  # sin credenciales

    with caplog.at_level(logging.ERROR):
        enviador = composicion.enviador_push()
        composicion.enviador_push()  # la segunda vez no vuelve a registrar el error

    assert enviador is None
    assert caplog.text.count("Push deshabilitado por configuración inválida") == 1


def test_el_servicio_armado_para_la_base_usa_el_canal_del_proceso(entorno_limpio) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sesion = sessionmaker(bind=engine)()

    servicio = composicion.crear_servicio_notificaciones(sesion)

    assert isinstance(servicio, ServicioNotificaciones)
    assert servicio._enviador is composicion.enviador_push()
    sesion.close()
    engine.dispose()
