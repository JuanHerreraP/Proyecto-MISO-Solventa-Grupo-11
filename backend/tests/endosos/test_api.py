"""API de endosos: opciones, simulación, confirmación, historial y descarga (HU16)."""

import hashlib

import pytest
from fastapi.testclient import TestClient

from app.api.cotizaciones import ActorCotizacion, TipoActorCotizacion, actor_actual
from app.api.endosos import obtener_servicio
from app.identidad.modelos import Rol
from app.main import app
from tests.endosos.fabrica import CLIENTE, POLIZA, crear_entorno

RUTA = f"/api/v1/polizas/{POLIZA}/endosos"
ITP = {"codigo": "INCAPACIDAD_TOTAL_PERMANENTE", "suma_asegurada": "50000000.00"}
BENEFICIARIOS = [
    {
        "nombre_completo": "Mateo Gómez",
        "tipo_documento": "CC",
        "numero_documento": "1098765432",
        "parentesco": "Hijo",
        "porcentaje": "60",
    },
    {
        "nombre_completo": "Sofía Gómez",
        "tipo_documento": "CC",
        "numero_documento": "1098765433",
        "parentesco": "Hija",
        "porcentaje": "40",
    },
]


def actor(rol=Rol.CLIENTE, actor_id=CLIENTE, tipo=TipoActorCotizacion.USUARIO):
    return lambda: ActorCotizacion(tipo=tipo, actor_id=actor_id, rol=rol)


@pytest.fixture
def entorno():
    e = crear_entorno()
    app.dependency_overrides[obtener_servicio] = lambda: e.servicio
    app.dependency_overrides[actor_actual] = actor()
    yield TestClient(app), e
    app.dependency_overrides.clear()


def test_opciones_de_una_poliza_de_vida(entorno) -> None:
    cliente, _ = entorno

    respuesta = cliente.get(f"{RUTA}/opciones")

    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert cuerpo["modificable"] is True
    assert cuerpo["admite_beneficiarios"] is True
    assert cuerpo["max_beneficiarios"] == 10
    disponibles = {c["codigo"]: c for c in cuerpo["coberturas_disponibles"]}
    assert set(disponibles) == {
        "INCAPACIDAD_TOTAL_PERMANENTE",
        "ENFERMEDADES_GRAVES",
        "AUXILIO_FUNERARIO",
    }
    # Topado por la suma de la cobertura principal (100 millones).
    assert disponibles["INCAPACIDAD_TOTAL_PERMANENTE"]["suma_maxima"] == "100000000.00"


def test_simular_muestra_el_ajuste_sin_guardar(entorno) -> None:
    cliente, e = entorno

    respuesta = cliente.post(f"{RUTA}/simulacion", json={"coberturas_opcionales": [ITP]})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["ajuste_prima"] == "36600.00"
    assert cuerpo["concepto_ajuste"] == "COBRO"
    assert cuerpo["prima_nueva"] == "186600.00"
    assert cuerpo["dias_restantes"] == 183
    assert e.endosos.listar_por_poliza(POLIZA) == []


def test_confirmar_emite_el_endoso_y_lo_ofrece_para_descargar(entorno) -> None:
    cliente, e = entorno

    respuesta = cliente.post(
        RUTA,
        json={"coberturas_opcionales": [ITP], "acepta_condiciones": True},
        headers={"Idempotency-Key": "abc-123"},
    )

    assert respuesta.status_code == 201
    endoso = respuesta.json()
    assert endoso["numero_endoso"] == 1
    assert endoso["concepto_ajuste"] == "COBRO"
    assert "ip_solicitante" not in endoso
    assert e.polizas.obtener(POLIZA).prima_total == 186600

    documento = cliente.get(f"{RUTA}/{endoso['endoso_id']}/documento")
    assert documento.status_code == 200
    assert documento.headers["content-type"] == "application/pdf"
    assert documento.headers["content-disposition"] == (
        'attachment; filename="endoso-SOL-2026-VIDA0001-001.pdf"'
    )
    assert documento.headers["x-huella-documento"] == hashlib.sha256(documento.content).hexdigest()
    assert documento.headers["x-huella-documento"] == endoso["huella_documento"]


def test_repetir_la_confirmacion_con_la_misma_clave_no_duplica(entorno) -> None:
    cliente, e = entorno
    cuerpo = {"beneficiarios": BENEFICIARIOS, "acepta_condiciones": True}

    primera = cliente.post(RUTA, json=cuerpo, headers={"Idempotency-Key": "abc-123"})
    segunda = cliente.post(RUTA, json=cuerpo, headers={"Idempotency-Key": "abc-123"})

    assert primera.status_code == 201
    assert segunda.status_code == 200
    assert segunda.json()["endoso_id"] == primera.json()["endoso_id"]
    assert len(e.endosos.listar_por_poliza(POLIZA)) == 1

    otra = cliente.post(
        RUTA,
        json={"coberturas_opcionales": [ITP], "acepta_condiciones": True},
        headers={"Idempotency-Key": "abc-123"},
    )
    assert otra.status_code == 409
    assert otra.json()["detail"]["codigo"] == "CLAVE_IDEMPOTENCIA_REUTILIZADA"


def test_confirmar_exige_aceptar_los_cambios(entorno) -> None:
    cliente, e = entorno

    respuesta = cliente.post(RUTA, json={"coberturas_opcionales": [ITP]})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "CONFIRMACION_REQUERIDA"
    assert e.endosos.listar_por_poliza(POLIZA) == []


def test_los_porcentajes_que_no_suman_100_se_rechazan_con_su_codigo(entorno) -> None:
    cliente, _ = entorno
    incompletos = [dict(BENEFICIARIOS[0], porcentaje="70"), BENEFICIARIOS[1]]

    respuesta = cliente.post(f"{RUTA}/simulacion", json={"beneficiarios": incompletos})

    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"]
    assert detalle["codigo"] == "PORCENTAJES_NO_SUMAN_100"
    assert detalle["campo"] == "beneficiarios"


def test_una_solicitud_sin_cambios_se_rechaza(entorno) -> None:
    cliente, _ = entorno

    respuesta = cliente.post(f"{RUTA}/simulacion", json={})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "SIN_CAMBIOS"


def test_el_historial_lista_los_endosos(entorno) -> None:
    cliente, _ = entorno
    cliente.post(RUTA, json={"beneficiarios": BENEFICIARIOS, "acepta_condiciones": True})
    cliente.post(RUTA, json={"coberturas_opcionales": [ITP], "acepta_condiciones": True})

    historial = cliente.get(RUTA).json()["endosos"]

    assert [(x["numero_endoso"], x["tipo"]) for x in historial] == [
        (1, "BENEFICIARIOS"),
        (2, "COBERTURAS"),
    ]
    assert historial[0]["cambios"][0]["tipo"] == "BENEFICIARIO_AGREGADO"


def test_un_cliente_no_ve_ni_modifica_la_poliza_de_otro(entorno) -> None:
    cliente, _ = entorno
    app.dependency_overrides[actor_actual] = actor(actor_id="CLI-999")

    assert cliente.get(f"{RUTA}/opciones").status_code == 404
    assert cliente.post(f"{RUTA}/simulacion", json={"beneficiarios": []}).status_code == 404
    confirmar = cliente.post(RUTA, json={"beneficiarios": [], "acepta_condiciones": True})
    assert confirmar.status_code == 404
    assert confirmar.json()["detail"]["codigo"] == "POLIZA_NO_ENCONTRADA"
    assert cliente.get(RUTA).status_code == 404


def test_el_asesor_que_no_participo_recibe_403(entorno) -> None:
    cliente, _ = entorno
    app.dependency_overrides[actor_actual] = actor(Rol.ASESOR_VENTAS, "ASE-1")

    respuesta = cliente.get(f"{RUTA}/opciones")

    assert respuesta.status_code == 403
    assert respuesta.json()["detail"]["codigo"] == "ACCESO_DENEGADO"


@pytest.mark.parametrize(
    "actor_prueba",
    [
        actor(Rol.ANALISTA_RIESGOS, "ANA-1"),
        actor(None, "SOCIO-1", TipoActorCotizacion.SOCIO),
    ],
)
def test_otros_actores_no_modifican_polizas(entorno, actor_prueba) -> None:
    cliente, _ = entorno
    app.dependency_overrides[actor_actual] = actor_prueba

    assert cliente.get(f"{RUTA}/opciones").status_code == 403
    assert cliente.post(f"{RUTA}/simulacion", json={"beneficiarios": []}).status_code == 403


def test_una_poliza_vencida_responde_409(entorno) -> None:
    cliente, e = entorno
    e.reloj.ahora = e.reloj.ahora.replace(year=2027)

    respuesta = cliente.post(f"{RUTA}/simulacion", json={"coberturas_opcionales": [ITP]})

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "POLIZA_NO_MODIFICABLE"


def test_un_endoso_inexistente_responde_404(entorno) -> None:
    cliente, _ = entorno

    respuesta = cliente.get(f"{RUTA}/END-NADA/documento")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["codigo"] == "ENDOSO_NO_ENCONTRADO"
