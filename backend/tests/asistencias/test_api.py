"""Pruebas de la API de asistencia en sitio y prestadores cercanos (HU06)."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.asistencias import obtener_servicio
from app.api.seguridad import get_current_user
from app.asistencias.repositorio import (
    RepositorioAsistenciasEnMemoria,
    RepositorioPrestadoresEnMemoria,
)
from app.asistencias.servicio import ServicioAsistencias
from app.identidad.modelos import Rol
from app.main import app
from app.polizas.dominio.modelos import EstadoRegistroPoliza, RamoPoliza
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from tests.asistencias.fabrica import BOGOTA, MEDELLIN, MOSQUERA, prestador
from tests.billetera.fabrica import poliza

AHORA = datetime(2026, 10, 21, 15, 0, tzinfo=UTC)
CLIENTE = SimpleNamespace(id="CLI-001", email="ana@gmail.com", rol=Rol.CLIENTE.value)
RUTA_ASI = "/api/v1/asistencias"
RUTA_CER = "/api/v1/prestadores/cercanos"
DISPOSITIVOS = dict(ramo=RamoPoliza.PROTECCION_DISPOSITIVOS)


@pytest.fixture
def entorno():
    polizas = RepositorioPolizasEnMemoria()
    # POL-1: dispositivos vigente del cliente. POL-VIAJE: viaje vigente del cliente.
    polizas.guardar(poliza(**DISPOSITIVOS))
    polizas.guardar(poliza(poliza_id="POL-VIAJE", numero_poliza="SOL-VI-2", ramo=RamoPoliza.VIAJE))
    # POL-VIDA: sin servicios de asistencia.
    polizas.guardar(poliza(poliza_id="POL-VIDA", numero_poliza="SOL-VD-1", ramo=RamoPoliza.VIDA))
    prestadores = RepositorioPrestadoresEnMemoria()
    prestadores.guardar(prestador(prestador_id="PREST-TEC-001", latitud=4.7150, longitud=-74.0690))
    prestadores.guardar(
        prestador(prestador_id="PREST-TEC-LEJOS", latitud=MEDELLIN[0], longitud=MEDELLIN[1])
    )
    asistencias = RepositorioAsistenciasEnMemoria()
    servicio = ServicioAsistencias(
        prestadores=prestadores,
        asistencias=asistencias,
        polizas=polizas,
        reloj=lambda: AHORA,
    )
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    app.dependency_overrides[get_current_user] = lambda: CLIENTE
    yield TestClient(app), polizas, prestadores, asistencias
    app.dependency_overrides.clear()


def _cuerpo(**cambios) -> dict:
    datos = {
        "poliza_id": "POL-1",
        "prestador_id": "PREST-TEC-001",
        "servicio": "REPARACION_DISPOSITIVO",
        "latitud": BOGOTA[0],
        "longitud": BOGOTA[1],
        "observaciones": "El dispositivo no enciende.",
    }
    datos.update(cambios)
    return datos


# --- servicios por ramo -----------------------------------------------------------------


def test_servicios_dispositivos(entorno):
    cliente, *_ = entorno
    r = cliente.get(f"{RUTA_ASI}/servicios", params={"poliza_id": "POL-1"})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["ramo"] == "PROTECCION_DISPOSITIVOS"
    assert [s["codigo"] for s in cuerpo["servicios"]] == [
        "DIAGNOSTICO_TECNICO",
        "REPARACION_DISPOSITIVO",
    ]
    assert r.headers["Cache-Control"] == "no-store"


def test_servicios_viaje(entorno):
    cliente, *_ = entorno
    r = cliente.get(f"{RUTA_ASI}/servicios", params={"poliza_id": "POL-VIAJE"})
    assert r.status_code == 200
    assert [s["codigo"] for s in r.json()["servicios"]] == [
        "ASISTENCIA_MEDICA",
        "ASISTENCIA_VIAJERO",
    ]


def test_servicios_vida_lista_vacia_no_es_error(entorno):
    cliente, *_ = entorno
    r = cliente.get(f"{RUTA_ASI}/servicios", params={"poliza_id": "POL-VIDA"})
    assert r.status_code == 200
    assert r.json()["servicios"] == []


def test_servicios_poliza_ajena_403(entorno):
    cliente, polizas, *_ = entorno
    polizas.guardar(
        poliza(poliza_id="POL-X", cliente_id="OTRO", numero_poliza="SOL-X", **DISPOSITIVOS)
    )
    r = cliente.get(f"{RUTA_ASI}/servicios", params={"poliza_id": "POL-X"})
    assert r.status_code == 403
    assert r.json()["detail"]["codigo"] == "POLIZA_NO_AUTORIZADA"


# --- prestadores cercanos ---------------------------------------------------------------


def test_cercanos_ok_ordena_y_marca_no_store(entorno):
    cliente, *_ = entorno
    r = cliente.get(
        RUTA_CER,
        params={
            "poliza_id": "POL-1",
            "servicio": "REPARACION_DISPOSITIVO",
            "latitud": BOGOTA[0],
            "longitud": BOGOTA[1],
            "radio_km": 25,
        },
    )
    assert r.status_code == 200
    cuerpo = r.json()
    # Medellín queda fuera del radio de 25 km.
    assert [p["prestador_id"] for p in cuerpo["prestadores"]] == ["PREST-TEC-001"]
    assert cuerpo["prestadores"][0]["distancia_km"] >= 0
    assert r.headers["Cache-Control"] == "no-store"


def test_cercanos_radio_invalido_422(entorno):
    cliente, *_ = entorno
    r = cliente.get(
        RUTA_CER,
        params={
            "poliza_id": "POL-1",
            "servicio": "REPARACION_DISPOSITIVO",
            "latitud": BOGOTA[0],
            "longitud": BOGOTA[1],
            "radio_km": 500,
        },
    )
    # 422 por la validación de Query (fuera de [1, 100]).
    assert r.status_code == 422


def test_cercanos_servicio_incompatible_con_ramo_422(entorno):
    cliente, *_ = entorno
    r = cliente.get(
        RUTA_CER,
        params={
            "poliza_id": "POL-1",
            "servicio": "ASISTENCIA_MEDICA",
            "latitud": BOGOTA[0],
            "longitud": BOGOTA[1],
        },
    )
    assert r.status_code == 422
    assert r.json()["detail"]["codigo"] == "SERVICIO_NO_DISPONIBLE"


def test_cercanos_poliza_inexistente_404(entorno):
    cliente, *_ = entorno
    r = cliente.get(
        RUTA_CER,
        params={
            "poliza_id": "POL-404",
            "servicio": "REPARACION_DISPOSITIVO",
            "latitud": BOGOTA[0],
            "longitud": BOGOTA[1],
        },
    )
    assert r.status_code == 404
    assert r.json()["detail"]["codigo"] == "POLIZA_NO_ENCONTRADA"


def test_cercanos_en_mosquera_encuentra_los_de_mosquera(entorno):
    cliente, _, prestadores, _ = entorno
    prestadores.guardar(
        prestador(prestador_id="PREST-MOS", latitud=MOSQUERA[0], longitud=MOSQUERA[1])
    )
    r = cliente.get(
        RUTA_CER,
        params={
            "poliza_id": "POL-1",
            "servicio": "REPARACION_DISPOSITIVO",
            "latitud": MOSQUERA[0],
            "longitud": MOSQUERA[1],
            "radio_km": 5,
        },
    )
    ids = [p["prestador_id"] for p in r.json()["prestadores"]]
    assert "PREST-MOS" in ids
    assert "PREST-TEC-001" not in ids  # queda a ~17 km


# --- crear ------------------------------------------------------------------------------


def test_crear_201_fija_cliente_estado_creada(entorno):
    cliente, _, _, asistencias = entorno
    r = cliente.post(RUTA_ASI, json=_cuerpo())
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["estado"] == "SOLICITADA"
    assert cuerpo["servicio"] == "REPARACION_DISPOSITIVO"
    assert cuerpo["prestador"]["prestador_id"] == "PREST-TEC-001"
    assert cuerpo["creada_en"] is not None
    assert cuerpo["cancelada_en"] is None
    assert r.headers["Cache-Control"] == "no-store"
    # El cliente queda tomado de la sesión.
    assert asistencias.listar_por_cliente("CLI-001")[0].asistencia_id == cuerpo["asistencia_id"]


def test_crear_servicio_no_permitido_422(entorno):
    cliente, *_ = entorno
    # POL-VIAJE no ofrece reparación de dispositivos.
    r = cliente.post(RUTA_ASI, json=_cuerpo(poliza_id="POL-VIAJE"))
    assert r.status_code == 422
    assert r.json()["detail"]["codigo"] == "SERVICIO_NO_DISPONIBLE"


def test_crear_prestador_inexistente_404(entorno):
    cliente, *_ = entorno
    r = cliente.post(RUTA_ASI, json=_cuerpo(prestador_id="PREST-NO"))
    assert r.status_code == 404
    assert r.json()["detail"]["codigo"] == "PRESTADOR_NO_ENCONTRADO"


def test_crear_prestador_inactivo_409(entorno):
    cliente, _, prestadores, _ = entorno
    prestadores.guardar(prestador(prestador_id="PREST-OFF", activo=False))
    r = cliente.post(RUTA_ASI, json=_cuerpo(prestador_id="PREST-OFF"))
    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "PRESTADOR_NO_DISPONIBLE"


def test_crear_prestador_no_ofrece_servicio_422(entorno):
    cliente, _, prestadores, _ = entorno
    prestadores.guardar(prestador(prestador_id="PREST-DIAG", servicios=["DIAGNOSTICO_TECNICO"]))
    r = cliente.post(
        RUTA_ASI, json=_cuerpo(prestador_id="PREST-DIAG", servicio="REPARACION_DISPOSITIVO")
    )
    assert r.status_code == 422
    assert r.json()["detail"]["codigo"] == "SERVICIO_NO_OFRECIDO_POR_PRESTADOR"


def test_crear_poliza_vencida_409(entorno):
    cliente, polizas, *_ = entorno
    polizas.guardar(
        poliza(
            poliza_id="POL-VENC",
            numero_poliza="SOL-VENC",
            fecha_inicio=datetime(2024, 1, 1).date(),
            fecha_fin=datetime(2024, 12, 31).date(),
            **DISPOSITIVOS,
        )
    )
    r = cliente.post(RUTA_ASI, json=_cuerpo(poliza_id="POL-VENC"))
    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "POLIZA_NO_VIGENTE"


def test_crear_poliza_cancelada_409(entorno):
    cliente, polizas, *_ = entorno
    polizas.guardar(
        poliza(
            poliza_id="POL-CANC",
            numero_poliza="SOL-CANC",
            estado=EstadoRegistroPoliza.CANCELADA,
            **DISPOSITIVOS,
        )
    )
    r = cliente.post(RUTA_ASI, json=_cuerpo(poliza_id="POL-CANC"))
    assert r.status_code == 409


def test_crear_no_acepta_cliente_id_en_el_cuerpo(entorno):
    cliente, *_ = entorno
    r = cliente.post(RUTA_ASI, json=_cuerpo(cliente_id="OTRO"))
    # extra="forbid" rechaza campos no esperados.
    assert r.status_code == 422


# --- listar y cancelar ------------------------------------------------------------------


def test_listar_devuelve_solo_del_cliente(entorno):
    cliente, *_ = entorno
    creada = cliente.post(RUTA_ASI, json=_cuerpo()).json()
    r = cliente.get(RUTA_ASI)
    assert r.status_code == 200
    assert [a["asistencia_id"] for a in r.json()] == [creada["asistencia_id"]]
    assert r.headers["Cache-Control"] == "no-store"


def test_cancelar_cambia_estado_sin_eliminar(entorno):
    cliente, _, _, asistencias = entorno
    creada = cliente.post(RUTA_ASI, json=_cuerpo()).json()
    r = cliente.post(f"{RUTA_ASI}/{creada['asistencia_id']}/cancelacion")
    assert r.status_code == 200
    assert r.json()["estado"] == "CANCELADA"
    assert r.json()["cancelada_en"] is not None
    assert asistencias.obtener(creada["asistencia_id"]) is not None


def test_cancelar_dos_veces_409(entorno):
    cliente, *_ = entorno
    creada = cliente.post(RUTA_ASI, json=_cuerpo()).json()
    cliente.post(f"{RUTA_ASI}/{creada['asistencia_id']}/cancelacion")
    r = cliente.post(f"{RUTA_ASI}/{creada['asistencia_id']}/cancelacion")
    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "ASISTENCIA_YA_CANCELADA"


def test_cancelar_inexistente_404(entorno):
    cliente, *_ = entorno
    r = cliente.post(f"{RUTA_ASI}/ASI-NO/cancelacion")
    assert r.status_code == 404
    assert r.json()["detail"]["codigo"] == "ASISTENCIA_NO_ENCONTRADA"


def test_cancelar_asistencia_ajena_403(entorno):
    cliente, _, _, asistencias = entorno
    creada = cliente.post(RUTA_ASI, json=_cuerpo()).json()
    # Otro cliente autenticado intenta cancelar.
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="OTRO", email="otro@x.com", rol=Rol.CLIENTE.value
    )
    r = cliente.post(f"{RUTA_ASI}/{creada['asistencia_id']}/cancelacion")
    assert r.status_code == 403
    assert r.json()["detail"]["codigo"] == "ASISTENCIA_NO_AUTORIZADA"


# --- seguridad --------------------------------------------------------------------------


def test_sin_token_401():
    app.dependency_overrides.clear()
    r = TestClient(app).get(f"{RUTA_ASI}/servicios", params={"poliza_id": "POL-1"})
    assert r.status_code == 401


def test_rol_no_cliente_403(entorno):
    cliente, *_ = entorno
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="ASE-1", email="asesor@x.com", rol=Rol.ASESOR_VENTAS.value
    )
    r = cliente.get(f"{RUTA_ASI}/servicios", params={"poliza_id": "POL-1"})
    assert r.status_code == 403
