import pytest
from fastapi.testclient import TestClient

from app.api.cotizaciones import ActorCotizacion, TipoActorCotizacion, actor_actual
from app.api.firmas import obtener_servicio
from app.identidad.modelos import Rol
from app.main import app
from tests.firmas.fabrica import COTIZACION, crear_entorno

RUTA = f"/api/v1/firmas/{COTIZACION}"


def actor(rol=Rol.CLIENTE, actor_id="CLI-001"):
    return lambda: ActorCotizacion(tipo=TipoActorCotizacion.USUARIO, actor_id=actor_id, rol=rol)


@pytest.fixture
def entorno():
    e = crear_entorno()
    app.dependency_overrides[obtener_servicio] = lambda: e.servicio
    app.dependency_overrides[actor_actual] = actor()
    yield TestClient(app), e
    app.dependency_overrides.clear()


def preparar_otp(cliente):
    huella = cliente.get(RUTA).json()["huella_documento"]
    assert cliente.post(f"{RUTA}/otp", json={"canal": "SMS"}).status_code == 200
    return huella


def test_presenta_el_contrato(entorno):
    cliente, _ = entorno

    respuesta = cliente.get(RUTA)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "PENDIENTE"
    assert cuerpo["documento_integro"] is True
    assert cuerpo["contrato"]["titular"]["nombre_completo"] == "Laura Gómez"
    assert "otp_hash" not in cuerpo


def test_flujo_completo_de_firma(entorno):
    cliente, e = entorno
    huella = preparar_otp(cliente)

    respuesta = cliente.post(
        f"{RUTA}/firma",
        json={"codigo": e.ultimo_codigo, "huella_documento": huella},
        headers={"User-Agent": "navegador-pruebas"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "FIRMADA"
    assert cuerpo["firmado_en"] is not None
    assert cuerpo["ip_firmante"] == "testclient"
    assert cuerpo["referencia_proveedor"].startswith("SIM-")
    guardado = e.firmas.obtener_por_cotizacion(COTIZACION)
    assert guardado.user_agent == "navegador-pruebas"


def test_otp_incorrecto_informa_intentos_restantes(entorno):
    cliente, _ = entorno
    huella = preparar_otp(cliente)

    respuesta = cliente.post(f"{RUTA}/firma", json={"codigo": "000000", "huella_documento": huella})

    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"]
    assert detalle["codigo"] == "OTP_INCORRECTO"
    assert detalle["intentos_restantes"] == 2


def test_formato_invalido_no_devuelve_el_codigo_recibido(entorno):
    cliente, _ = entorno
    huella = preparar_otp(cliente)

    respuesta = cliente.post(f"{RUTA}/firma", json={"codigo": "12ab56", "huella_documento": huella})

    assert respuesta.status_code == 422
    assert "12ab56" not in respuesta.text


def test_reenvio_inmediato_responde_429(entorno):
    cliente, _ = entorno
    preparar_otp(cliente)

    respuesta = cliente.post(f"{RUTA}/otp", json={"canal": "SMS"})

    assert respuesta.status_code == 429
    assert respuesta.json()["detail"]["codigo"] == "ESPERA_REENVIO"


def test_sin_pago_aprobado_responde_409(entorno):
    cliente, e = entorno
    e.pagos._por_id.clear()

    respuesta = cliente.get(RUTA)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "PAGO_NO_APROBADO"


def test_huella_distinta_responde_409(entorno):
    cliente, e = entorno
    preparar_otp(cliente)

    respuesta = cliente.post(
        f"{RUTA}/firma", json={"codigo": e.ultimo_codigo, "huella_documento": "0" * 64}
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "DOCUMENTO_ALTERADO"


def test_proveedor_caido_responde_503(entorno):
    cliente, e = entorno
    cliente.get(RUTA)
    e.proveedor.disponible = False

    respuesta = cliente.post(f"{RUTA}/otp", json={"canal": "SMS"})

    assert respuesta.status_code == 503


def test_bloqueo_responde_423(entorno):
    cliente, e = entorno
    huella = cliente.get(RUTA).json()["huella_documento"]
    for _ in range(3):
        cliente.post(f"{RUTA}/otp", json={"canal": "SMS"})
        e.reloj.avanzar(seconds=31)
        for _ in range(3):
            ultima = cliente.post(
                f"{RUTA}/firma", json={"codigo": "000000", "huella_documento": huella}
            )

    assert ultima.status_code == 423
    assert cliente.get(RUTA).json()["estado"] == "BLOQUEADA"


def test_otro_cliente_no_ve_el_contrato(entorno):
    cliente, _ = entorno
    cliente.get(RUTA)
    app.dependency_overrides[actor_actual] = actor(actor_id="CLI-999")

    assert cliente.get(RUTA).status_code == 404


@pytest.mark.parametrize("rol", [Rol.ASESOR_VENTAS, Rol.OPERACIONES_SINIESTROS])
def test_solo_el_cliente_firma(entorno, rol):
    cliente, _ = entorno
    app.dependency_overrides[actor_actual] = actor(rol=rol)

    assert cliente.get(RUTA).status_code == 403


def test_sin_autenticacion_responde_401(entorno):
    cliente, _ = entorno
    app.dependency_overrides.pop(actor_actual)

    assert cliente.get(RUTA).status_code == 401
