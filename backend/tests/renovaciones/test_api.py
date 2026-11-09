"""API de renovación: propuesta, inicio, estado y errores (HU22)."""

import pytest
from fastapi.testclient import TestClient

from app.api.cotizaciones import ActorCotizacion, TipoActorCotizacion, actor_actual
from app.api.renovaciones import obtener_servicio
from app.identidad.modelos import Rol
from app.main import app
from tests.renovaciones.fabrica import CLIENTE, POLIZA, crear_entorno

RUTA = f"/api/v1/polizas/{POLIZA}/renovacion"
ID_RENOVACION = "REN-POL-VIDA-1-20270101"


def actor(rol=Rol.CLIENTE, actor_id=CLIENTE, tipo=TipoActorCotizacion.USUARIO):
    return lambda: ActorCotizacion(tipo=tipo, actor_id=actor_id, rol=rol)


def con_entorno(e, **actor_args):
    app.dependency_overrides[obtener_servicio] = lambda: e.servicio
    app.dependency_overrides[actor_actual] = actor(**actor_args)
    return TestClient(app)


@pytest.fixture
def entorno():
    e = crear_entorno()
    yield con_entorno(e), e
    app.dependency_overrides.clear()


def test_la_propuesta_muestra_vigencia_coberturas_y_prima(entorno) -> None:
    cliente, _ = entorno

    respuesta = cliente.get(RUTA)

    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert cuerpo["renovable"] is True and cuerpo["bloqueos"] == []
    assert cuerpo["nueva_vigencia"] == {"inicio": "2027-01-01", "fin": "2027-12-31"}
    assert cuerpo["vigencia_actual"] == {"inicio": "2026-01-01", "fin": "2026-12-31"}
    assert cuerpo["prima_actual"] == "150000.00"
    assert cuerpo["prima_nueva"] == "420000.00"
    assert cuerpo["coberturas"][0]["codigo"] == "FALLECIMIENTO"
    assert cuerpo["coberturas"][0]["principal"] is True
    assert len(cuerpo["condiciones"]) == 4
    assert cuerpo["renovacion"] is None


def test_iniciar_devuelve_lo_necesario_para_pagar_y_no_expone_auditoria(entorno) -> None:
    cliente, e = entorno

    respuesta = cliente.post(RUTA, headers={"Idempotency-Key": "k-1"})

    assert respuesta.status_code == 201
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert cuerpo["renovacion_id"] == ID_RENOVACION
    assert cuerpo["estado"] == "PENDIENTE_PAGO"
    assert cuerpo["prima_total"] == "420000.00" and cuerpo["moneda"] == "COP"
    assert cuerpo["nuevo_inicio"] == "2027-01-01" and cuerpo["nuevo_fin"] == "2027-12-31"
    assert e.cotizaciones.obtener(cuerpo["cotizacion_id"]) is not None
    for privado in ("clave_idempotencia", "ip_solicitante", "user_agent", "solicitado_por"):
        assert privado not in cuerpo


def test_repetir_el_inicio_responde_200_con_la_misma_renovacion(entorno) -> None:
    cliente, _ = entorno
    primera = cliente.post(RUTA, headers={"Idempotency-Key": "k-1"})

    segunda = cliente.post(RUTA, headers={"Idempotency-Key": "k-1"})
    sin_clave = cliente.post(RUTA)

    assert segunda.status_code == 200 and sin_clave.status_code == 200
    assert segunda.json() == primera.json() == sin_clave.json()


def test_la_propuesta_incluye_la_renovacion_en_curso(entorno) -> None:
    cliente, _ = entorno
    creada = cliente.post(RUTA).json()

    cuerpo = cliente.get(RUTA).json()

    assert cuerpo["renovacion"]["renovacion_id"] == creada["renovacion_id"]
    assert cuerpo["renovacion"]["cotizacion_id"] == creada["cotizacion_id"]


def test_el_pago_aprobado_renueva_y_el_estado_lo_informa(entorno) -> None:
    cliente, e = entorno
    creada = cliente.post(RUTA).json()
    assert cliente.get(f"{RUTA}/{ID_RENOVACION}").json()["estado"] == "PENDIENTE_PAGO"

    e.pagar(creada["cotizacion_id"])

    estado = cliente.get(f"{RUTA}/{ID_RENOVACION}")
    assert estado.status_code == 200
    assert estado.json()["estado"] == "APLICADA"
    assert estado.json()["pago_id"] is not None
    propuesta = cliente.get(RUTA).json()
    assert propuesta["renovable"] is False
    assert propuesta["bloqueos"][0]["codigo"] == "YA_RENOVADA"
    assert propuesta["renovacion"] is None


def test_una_renovacion_inexistente_o_de_otra_poliza_responde_404(entorno) -> None:
    cliente, _ = entorno

    respuesta = cliente.get(f"{RUTA}/REN-NO-EXISTE")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["codigo"] == "RENOVACION_NO_ENCONTRADA"


def test_fuera_de_la_ventana_responde_409_con_el_motivo() -> None:
    e = crear_entorno()
    e.reloj.ahora = e.reloj.ahora.replace(month=6)
    cliente = con_entorno(e)
    try:
        propuesta = cliente.get(RUTA).json()
        respuesta = cliente.post(RUTA)
    finally:
        app.dependency_overrides.clear()

    assert propuesta["renovable"] is False
    assert propuesta["bloqueos"][0]["codigo"] == "FUERA_DE_VENTANA"
    assert respuesta.status_code == 409
    detalle = respuesta.json()["detail"]
    assert detalle["codigo"] == "FUERA_DE_VENTANA"
    assert "01/12/2026" in detalle["mensaje"]
    assert detalle["bloqueos"][0]["codigo"] == "FUERA_DE_VENTANA"
    assert e.renovaciones.por_poliza(POLIZA) == []


def test_una_poliza_ajena_responde_404(entorno) -> None:
    cliente, _ = entorno
    app.dependency_overrides[actor_actual] = actor(actor_id="CLI-OTRO")

    assert cliente.get(RUTA).status_code == 404
    respuesta = cliente.post(RUTA)
    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["codigo"] == "POLIZA_NO_ENCONTRADA"


def test_un_rol_sin_permiso_recibe_403(entorno) -> None:
    cliente, e = entorno
    app.dependency_overrides[actor_actual] = actor(rol=Rol.ANALISTA_RIESGOS, actor_id="ANA-1")

    assert cliente.get(RUTA).status_code == 403
    assert cliente.post(RUTA).status_code == 403
    assert e.renovaciones.por_poliza(POLIZA) == []


def test_el_asesor_renueva_la_poliza_de_su_venta_y_no_la_de_otro() -> None:
    propia = crear_entorno(asesor_id="ASE-1")
    ajena = crear_entorno(asesor_id="ASE-2")
    try:
        cliente = con_entorno(propia, rol=Rol.ASESOR_VENTAS, actor_id="ASE-1")
        assert cliente.post(RUTA).status_code == 201

        cliente = con_entorno(ajena, rol=Rol.ASESOR_VENTAS, actor_id="ASE-1")
        respuesta = cliente.post(RUTA)
        assert respuesta.status_code == 403
        assert respuesta.json()["detail"]["codigo"] == "ACCESO_DENEGADO"
        assert cliente.get(RUTA).status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_un_perfil_rechazado_responde_409_riesgo_no_asegurable() -> None:
    from app.perfilamiento.dominio.modelos import Dictamen
    from tests.renovaciones.fabrica import perfil

    e = crear_entorno(perfil_riesgo=perfil(dictamen=Dictamen.RECHAZADO, factor=None))
    cliente = con_entorno(e)
    try:
        respuesta = cliente.post(RUTA)
    finally:
        app.dependency_overrides.clear()

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "RIESGO_NO_ASEGURABLE"
