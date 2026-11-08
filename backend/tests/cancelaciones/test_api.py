"""API de cancelación: condiciones, confirmación, idempotencia y errores (HU22)."""

import pytest
from fastapi.testclient import TestClient

from app.api.cancelaciones import obtener_servicio
from app.api.cotizaciones import ActorCotizacion, TipoActorCotizacion, actor_actual
from app.identidad.modelos import Rol
from app.main import app
from app.siniestros.modelos import EstadoSiniestro
from tests.cancelaciones.fabrica import CLIENTE, POLIZA, crear_entorno, siniestro

RUTA = f"/api/v1/polizas/{POLIZA}/cancelacion"
CUERPO = {"motivo": "PRECIO_ALTO", "detalle": "Muy caro", "confirmo": True}


def actor(rol=Rol.CLIENTE, actor_id=CLIENTE, tipo=TipoActorCotizacion.USUARIO):
    return lambda: ActorCotizacion(tipo=tipo, actor_id=actor_id, rol=rol)


@pytest.fixture
def entorno():
    e = crear_entorno()
    app.dependency_overrides[obtener_servicio] = lambda: e.servicio
    app.dependency_overrides[actor_actual] = actor()
    yield TestClient(app), e
    app.dependency_overrides.clear()


def test_consultar_muestra_condiciones_consecuencias_y_saldo(entorno) -> None:
    cliente, _ = entorno

    respuesta = cliente.get(RUTA)

    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert cuerpo["cancelable"] is True
    assert cuerpo["bloqueos"] == []
    assert cuerpo["saldo_estimado"] == "74794.52"
    assert cuerpo["dias_no_transcurridos"] == 182
    assert len(cuerpo["consecuencias"]) == 4
    assert {m["codigo"] for m in cuerpo["motivos"]} >= {"PRECIO_ALTO", "OTRO"}
    assert cuerpo["cancelacion"] is None


def test_consultar_informa_el_siniestro_que_bloquea(entorno) -> None:
    cliente, e = entorno
    e.siniestros.guardar(siniestro(EstadoSiniestro.EN_EVALUACION))

    cuerpo = cliente.get(RUTA).json()

    assert cuerpo["cancelable"] is False
    assert cuerpo["bloqueos"][0]["codigo"] == "SINIESTRO_EN_TRAMITE"
    assert cuerpo["bloqueos"][0]["siniestros"] == ["SIN-1"]


def test_confirmar_cancela_y_no_expone_datos_de_auditoria(entorno) -> None:
    cliente, e = entorno

    respuesta = cliente.post(RUTA, json=CUERPO, headers={"Idempotency-Key": "k-1"})

    assert respuesta.status_code == 201
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert cuerpo["saldo_estimado"] == "74794.52"
    assert cuerpo["estado_devolucion"] == "PENDIENTE"
    assert cuerpo["motivo"] == "PRECIO_ALTO"
    for privado in ("huella_solicitud", "ip_solicitante", "user_agent", "clave_idempotencia"):
        assert privado not in cuerpo
    assert e.polizas.obtener(POLIZA).estado.value == "CANCELADA"
    assert cliente.get(RUTA).json()["cancelacion"]["cancelacion_id"] == cuerpo["cancelacion_id"]


def test_repetir_con_la_misma_clave_responde_200_con_la_misma_cancelacion(entorno) -> None:
    cliente, _ = entorno
    primera = cliente.post(RUTA, json=CUERPO, headers={"Idempotency-Key": "k-1"})

    segunda = cliente.post(RUTA, json=CUERPO, headers={"Idempotency-Key": "k-1"})

    assert segunda.status_code == 200
    assert segunda.json() == primera.json()


def test_reusar_la_clave_con_otro_cuerpo_responde_409(entorno) -> None:
    cliente, _ = entorno
    cliente.post(RUTA, json=CUERPO, headers={"Idempotency-Key": "k-1"})

    respuesta = cliente.post(
        RUTA, json={**CUERPO, "motivo": "OTRO"}, headers={"Idempotency-Key": "k-1"}
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "CLAVE_IDEMPOTENCIA_REUTILIZADA"


def test_sin_confirmacion_responde_422_y_no_cancela(entorno) -> None:
    cliente, e = entorno

    respuesta = cliente.post(RUTA, json={"motivo": "OTRO", "confirmo": False})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "CONFIRMACION_REQUERIDA"
    assert e.polizas.obtener(POLIZA).estado.value == "VIGENTE"


def test_un_motivo_desconocido_responde_422(entorno) -> None:
    cliente, _ = entorno

    assert cliente.post(RUTA, json={"motivo": "PORQUE_SI", "confirmo": True}).status_code == 422


def test_con_siniestro_en_tramite_responde_409_y_la_poliza_queda_igual(entorno) -> None:
    cliente, e = entorno
    e.siniestros.guardar(siniestro(EstadoSiniestro.REGISTRADO))

    respuesta = cliente.post(RUTA, json=CUERPO)

    assert respuesta.status_code == 409
    detalle = respuesta.json()["detail"]
    assert detalle["codigo"] == "SINIESTRO_EN_TRAMITE"
    assert detalle["bloqueos"][0]["siniestros"] == ["SIN-1"]
    assert e.polizas.obtener(POLIZA).estado.value == "VIGENTE"


def test_cancelar_una_poliza_ya_cancelada_responde_409(entorno) -> None:
    cliente, _ = entorno
    cliente.post(RUTA, json=CUERPO)

    respuesta = cliente.post(RUTA, json=CUERPO)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "POLIZA_NO_VIGENTE"


def test_una_poliza_ajena_responde_404(entorno) -> None:
    cliente, _ = entorno
    app.dependency_overrides[actor_actual] = actor(actor_id="CLI-OTRO")

    assert cliente.get(RUTA).status_code == 404
    respuesta = cliente.post(RUTA, json=CUERPO)
    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["codigo"] == "POLIZA_NO_ENCONTRADA"


def test_un_rol_sin_permiso_recibe_403(entorno) -> None:
    cliente, e = entorno
    app.dependency_overrides[actor_actual] = actor(rol=Rol.ANALISTA_RIESGOS, actor_id="ANA-1")

    assert cliente.get(RUTA).status_code == 403
    assert cliente.post(RUTA, json=CUERPO).status_code == 403
    assert e.polizas.obtener(POLIZA).estado.value == "VIGENTE"


def test_el_asesor_cancela_la_poliza_de_su_venta_asistida() -> None:
    e = crear_entorno(asesor_id="ASE-1")
    app.dependency_overrides[obtener_servicio] = lambda: e.servicio
    app.dependency_overrides[actor_actual] = actor(rol=Rol.ASESOR_VENTAS, actor_id="ASE-1")
    try:
        cliente = TestClient(app)
        assert cliente.get(RUTA).json()["cancelable"] is True

        respuesta = cliente.post(RUTA, json=CUERPO)

        assert respuesta.status_code == 201
        assert e.cancelaciones.por_poliza(POLIZA).rol_solicitante == "ASESOR_VENTAS"
        assert e.polizas.obtener(POLIZA).estado.value == "CANCELADA"
    finally:
        app.dependency_overrides.clear()


def test_el_asesor_no_cancela_la_poliza_de_otro_asesor() -> None:
    e = crear_entorno(asesor_id="ASE-2")
    app.dependency_overrides[obtener_servicio] = lambda: e.servicio
    app.dependency_overrides[actor_actual] = actor(rol=Rol.ASESOR_VENTAS, actor_id="ASE-1")
    try:
        cliente = TestClient(app)

        respuesta = cliente.post(RUTA, json=CUERPO)

        assert respuesta.status_code == 403
        assert respuesta.json()["detail"]["codigo"] == "ACCESO_DENEGADO"
        assert cliente.get(RUTA).status_code == 403
        assert e.polizas.obtener(POLIZA).estado.value == "VIGENTE"
    finally:
        app.dependency_overrides.clear()
