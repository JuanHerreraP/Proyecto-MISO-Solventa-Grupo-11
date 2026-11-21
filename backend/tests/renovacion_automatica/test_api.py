"""API de la renovación automática: preferencia, documento y ejecución de la tarea (HU17)."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import renovacion_automatica as api
from app.api.cotizaciones import ActorCotizacion, TipoActorCotizacion, actor_actual
from app.api.seguridad import get_current_user
from app.identidad.modelos import Rol
from app.main import app
from tests.renovacion_automatica.fabrica import (
    CLIENTE,
    POLIZA,
    TARJETA,
    VENCIMIENTO,
    a_las_10,
    crear_entorno_automatico,
)
from tests.renovaciones.fabrica import ASESOR

RUTA = f"/api/v1/polizas/{POLIZA}/renovacion-automatica"
EJECUCIONES = "/api/v1/operaciones/renovaciones-automaticas/ejecuciones"


def como(rol: Rol = Rol.CLIENTE, actor_id: str = CLIENTE) -> None:
    app.dependency_overrides[actor_actual] = lambda: ActorCotizacion(
        tipo=TipoActorCotizacion.USUARIO, actor_id=actor_id, rol=rol
    )


@pytest.fixture
def entorno():
    e = crear_entorno_automatico(asesor_id=ASESOR.actor_id)
    app.dependency_overrides[api.obtener_servicio] = lambda: e.servicio
    como()
    yield TestClient(app), e
    app.dependency_overrides.clear()


def test_por_defecto_esta_activa_sin_tarjeta_y_muestra_las_fechas(entorno) -> None:
    cliente, _ = entorno

    respuesta = cliente.get(RUTA)

    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert cuerpo["disponible"] is True and cuerpo["activa"] is True
    assert cuerpo["tarjeta"] is None
    assert cuerpo["vence_el"] == "2026-12-31"
    assert cuerpo["preaviso_desde"] == "2026-12-01"
    assert cuerpo["cobro_programado_para"] == "2026-12-31"
    assert cuerpo["ultimo_ciclo"] is None


def test_registrar_la_tarjeta_solo_devuelve_los_ultimos_digitos(entorno) -> None:
    cliente, e = entorno

    respuesta = cliente.put(
        RUTA,
        json={
            "activa": True,
            "tarjeta": {"token_tarjeta": "tok_visa_aprobado_4242", "ultimos_digitos": "4242"},
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["tarjeta"] == {"ultimos_digitos": "4242"}
    assert "tok_visa" not in respuesta.text
    assert e.preferencias.obtener(POLIZA).medio_pago.token_tarjeta == "tok_visa_aprobado_4242"


def test_desactivar_conserva_la_tarjeta_y_quitarla_la_elimina(entorno) -> None:
    cliente, e = entorno
    e.registrar(TARJETA)

    desactivada = cliente.put(RUTA, json={"activa": False})
    quitada = cliente.put(RUTA, json={"activa": True, "quitar_tarjeta": True})

    assert desactivada.json()["activa"] is False
    assert desactivada.json()["tarjeta"] == {"ultimos_digitos": "4242"}
    assert quitada.json()["activa"] is True and quitada.json()["tarjeta"] is None


def test_un_numero_de_tarjeta_se_rechaza_sin_devolverlo(entorno) -> None:
    cliente, e = entorno

    respuesta = cliente.put(
        RUTA, json={"activa": True, "tarjeta": {"token_tarjeta": "4111111111111111"}}
    )

    assert respuesta.status_code == 422
    assert "4111111111111111" not in respuesta.text
    assert e.preferencias.obtener(POLIZA) is None


def test_el_asesor_no_registra_tarjetas(entorno) -> None:
    cliente, _ = entorno
    como(Rol.ASESOR_VENTAS, ASESOR.actor_id)

    consulta = cliente.get(RUTA)
    tarjeta = cliente.put(
        RUTA, json={"activa": True, "tarjeta": {"token_tarjeta": "tok_visa_aprobado_4242"}}
    )
    desactivar = cliente.put(RUTA, json={"activa": False})

    assert consulta.status_code == 200
    assert tarjeta.status_code == 403
    assert tarjeta.json()["detail"]["codigo"] == "ACCESO_DENEGADO"
    assert desactivar.status_code == 200 and desactivar.json()["activa"] is False


def test_una_poliza_ajena_no_existe(entorno) -> None:
    cliente, _ = entorno
    como(actor_id="CLI-999")

    respuesta = cliente.get(RUTA)

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["codigo"] == "POLIZA_NO_ENCONTRADA"


def test_tras_renovar_muestra_el_ciclo_y_entrega_el_documento(entorno) -> None:
    cliente, e = entorno
    e.registrar(TARJETA)
    e.ejecutar_el(VENCIMIENTO)

    cuerpo = cliente.get(RUTA).json()
    ciclo = cuerpo["ultimo_ciclo"]
    assert ciclo["estado"] == "RENOVADA" and ciclo["documento_disponible"] is True
    assert ciclo["vence_el"] == "2026-12-31"
    assert cuerpo["vence_el"] == "2027-12-31"  # La póliza ya tiene la nueva vigencia.

    documento = cliente.get(f"{RUTA}/{ciclo['renovacion_id']}/documento")

    assert documento.status_code == 200
    assert documento.headers["content-type"] == "application/pdf"
    assert documento.headers["x-huella-documento"] == e.ciclo().huella_documento
    assert "renovacion-SOL-2026-VIDA0001-20261231.pdf" in documento.headers["content-disposition"]
    assert documento.content.startswith(b"%PDF")


def test_documento_de_una_renovacion_inexistente(entorno) -> None:
    cliente, _ = entorno

    respuesta = cliente.get(f"{RUTA}/REN-NO-EXISTE/documento")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["codigo"] == "RENOVACION_NO_ENCONTRADA"


def test_operaciones_ejecuta_la_tarea_a_demanda(entorno) -> None:
    cliente, e = entorno
    e.registrar(TARJETA)
    e.base.reloj.ahora = a_las_10(VENCIMIENTO)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="OPS-1", rol=Rol.SERVICIO_INTERNO.value, email="ops@example.com"
    )

    respuesta = cliente.post(EJECUCIONES)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["fecha"] == "2026-12-31"
    assert cuerpo["renovadas"] == 1 and cuerpo["contratos_enviados"] == 1


def test_un_cliente_no_puede_ejecutar_la_tarea(entorno) -> None:
    cliente, _ = entorno
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=CLIENTE, rol=Rol.CLIENTE.value, email="laura@example.com"
    )

    respuesta = cliente.post(EJECUCIONES)

    assert respuesta.status_code == 403
