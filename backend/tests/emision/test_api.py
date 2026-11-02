import hashlib

import pytest
from fastapi.testclient import TestClient

from app.api.cotizaciones import ActorCotizacion, TipoActorCotizacion, actor_actual
from app.api.emision import obtener_despachador, obtener_emision
from app.api.firmas import obtener_servicio
from app.identidad.modelos import Rol
from app.main import app
from app.polizas.emision import poliza_id_de
from tests.emision.fabrica import crear_entorno
from tests.firmas.fabrica import COTIZACION

RUTA_FIRMA = f"/api/v1/firmas/{COTIZACION}"
POLIZA = poliza_id_de(COTIZACION)
RUTA_DOCUMENTO = f"/api/v1/polizas/{POLIZA}/documento"


def actor(rol=Rol.CLIENTE, actor_id="CLI-001", tipo=TipoActorCotizacion.USUARIO):
    return lambda: ActorCotizacion(tipo=tipo, actor_id=actor_id, rol=rol)


@pytest.fixture
def entorno():
    e = crear_entorno()
    app.dependency_overrides[obtener_servicio] = lambda: e.firmas_servicio
    app.dependency_overrides[obtener_emision] = lambda: e.emision
    app.dependency_overrides[obtener_despachador] = lambda: e.emision.notificar
    app.dependency_overrides[actor_actual] = actor()
    yield TestClient(app), e
    app.dependency_overrides.clear()


def firmar(cliente, e):
    huella = cliente.get(RUTA_FIRMA).json()["huella_documento"]
    assert cliente.post(f"{RUTA_FIRMA}/otp", json={"canal": "SMS"}).status_code == 200
    return cliente.post(
        f"{RUTA_FIRMA}/firma",
        json={"codigo": e.ultimo_codigo, "huella_documento": huella},
    )


def test_antes_de_firmar_no_hay_poliza_ni_documento(entorno) -> None:
    cliente, _ = entorno

    assert cliente.get(RUTA_FIRMA).json()["poliza_id"] is None
    assert cliente.get(RUTA_DOCUMENTO).status_code == 404


def test_al_firmar_se_emite_la_poliza_y_se_ofrece_su_descarga(entorno) -> None:
    cliente, e = entorno

    respuesta = firmar(cliente, e)

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "FIRMADA"
    assert respuesta.json()["poliza_id"] == POLIZA
    documento = cliente.get(RUTA_DOCUMENTO)
    assert documento.status_code == 200
    assert documento.headers["content-type"] == "application/pdf"
    assert documento.headers["content-disposition"].startswith('attachment; filename="poliza-SOL-')
    assert documento.headers["cache-control"] == "no-store"
    assert documento.content.startswith(b"%PDF")
    assert documento.headers["x-huella-documento"] == hashlib.sha256(documento.content).hexdigest()


def test_el_correo_y_la_confirmacion_salen_despues_de_responder(entorno) -> None:
    cliente, e = entorno

    firmar(cliente, e)

    assert len(e.comunicaciones.correos) == 1
    assert e.comunicaciones.correos[0].destinatario == "laura@example.com"
    assert e.comunicaciones.correos[0].adjunto_pdf.startswith(b"%PDF")
    assert len(e.comunicaciones.notificaciones) == 1


def test_repetir_la_firma_no_duplica_poliza_documento_ni_correo(entorno) -> None:
    cliente, e = entorno
    primera = firmar(cliente, e)
    huella = primera.json()["huella_documento"]

    repetida = cliente.post(
        f"{RUTA_FIRMA}/firma", json={"codigo": "000000", "huella_documento": huella}
    )

    assert repetida.status_code == 200
    assert repetida.json()["poliza_id"] == primera.json()["poliza_id"]
    assert len(e.polizas.listar_por_cliente("CLI-001")) == 1
    assert len(e.comunicaciones.correos) == 1
    assert len(e.comunicaciones.notificaciones) == 1


def test_un_cliente_no_descarga_la_poliza_de_otro(entorno) -> None:
    cliente, e = entorno
    firmar(cliente, e)
    app.dependency_overrides[actor_actual] = actor(actor_id="CLI-999")

    assert cliente.get(RUTA_DOCUMENTO).status_code == 404


def test_el_asesor_descarga_solo_si_participo_en_la_venta(entorno) -> None:
    cliente, e = entorno
    asistida = e.cotizaciones.obtener(COTIZACION).model_copy(update={"asesor_id": "ASE-1"})
    e.cotizaciones.guardar(asistida)
    firmar(cliente, e)

    app.dependency_overrides[actor_actual] = actor(Rol.ASESOR_VENTAS, "ASE-1")
    permitido = cliente.get(RUTA_DOCUMENTO)
    app.dependency_overrides[actor_actual] = actor(Rol.ASESOR_VENTAS, "ASE-2")
    ajeno = cliente.get(RUTA_DOCUMENTO)

    assert permitido.status_code == 200
    assert permitido.content.startswith(b"%PDF")
    assert ajeno.status_code == 403


def test_otros_roles_y_socios_no_descargan_documentos(entorno) -> None:
    cliente, e = entorno
    firmar(cliente, e)

    app.dependency_overrides[actor_actual] = actor(Rol.SERVICIO_INTERNO, "SVC-1")
    assert cliente.get(RUTA_DOCUMENTO).status_code == 403
    app.dependency_overrides[actor_actual] = actor(None, "SOC-1", TipoActorCotizacion.SOCIO)
    assert cliente.get(RUTA_DOCUMENTO).status_code == 403


def test_un_documento_alterado_se_rechaza(entorno) -> None:
    cliente, e = entorno
    firmar(cliente, e)
    clave = e.documentos.obtener(POLIZA).clave_almacenamiento
    e.almacen._por_clave[clave] = b"%PDF-falso"

    respuesta = cliente.get(RUTA_DOCUMENTO)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "DOCUMENTO_ALTERADO"
