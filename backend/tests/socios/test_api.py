import pytest
from fastapi.testclient import TestClient

from app.api.socios import obtener_servicio
from app.main import app
from app.socios.dominio.auditoria import RepositorioAuditoriaSociosEnMemoria
from app.socios.dominio.tenant import AprovisionadorTenantsEnMemoria
from app.socios.repositorio import RepositorioSociosEnMemoria
from app.socios.servicio import ServicioSocios
from tests.socios.fabrica import solicitud_alta

RUTA = "/api/v1/socios"
INGENIERO = {"X-Rol": "INGENIERO_INTEGRACIONES", "X-Actor-Id": "ingeniero-01"}
CLIENTE = {"X-Rol": "CLIENTE", "X-Actor-Id": "cliente-01"}


@pytest.fixture
def cliente():
    servicio = ServicioSocios(
        RepositorioSociosEnMemoria(),
        AprovisionadorTenantsEnMemoria(),
        RepositorioAuditoriaSociosEnMemoria(),
    )
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    yield TestClient(app)
    app.dependency_overrides.clear()


def cuerpo() -> dict:
    return solicitud_alta().model_dump(mode="json")


def test_da_de_alta_y_aprovisiona_el_socio(cliente) -> None:
    respuesta = cliente.post(RUTA, json=cuerpo(), headers=INGENIERO)

    assert respuesta.status_code == 201
    assert respuesta.json()["socio_id"].startswith("SOCIO-")
    assert respuesta.json()["tenant_id"].startswith("TENANT-")
    assert respuesta.json()["estado"] == "ACTIVO"


def test_nit_duplicado_devuelve_conflicto(cliente) -> None:
    cliente.post(RUTA, json=cuerpo(), headers=INGENIERO)

    respuesta = cliente.post(RUTA, json=cuerpo(), headers=INGENIERO)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Ya existe un socio registrado con el mismo NIT."


def test_entrada_incompleta_se_rechaza(cliente) -> None:
    incompleto = cuerpo()
    del incompleto["razon_social"]

    assert cliente.post(RUTA, json=incompleto, headers=INGENIERO).status_code == 422


def test_cliente_no_puede_registrar_socios(cliente) -> None:
    assert cliente.post(RUTA, json=cuerpo(), headers=CLIENTE).status_code == 403


def test_solicitud_sin_identidad_se_rechaza(cliente) -> None:
    assert cliente.post(RUTA, json=cuerpo()).status_code == 401


def test_consulta_y_modifica_la_configuracion(cliente) -> None:
    creado = cliente.post(RUTA, json=cuerpo(), headers=INGENIERO).json()

    actualizado = cliente.patch(
        f"{RUTA}/{creado['socio_id']}",
        json={"razon_social": "Banco Andes Digital S.A."},
        headers=INGENIERO,
    )
    consultado = cliente.get(f"{RUTA}/{creado['socio_id']}", headers=INGENIERO)

    assert actualizado.status_code == 200
    assert actualizado.json()["razon_social"] == "Banco Andes Digital S.A."
    assert consultado.json() == actualizado.json()


def test_socio_inexistente_devuelve_no_encontrado(cliente) -> None:
    assert cliente.get(f"{RUTA}/NO-EXISTE", headers=INGENIERO).status_code == 404
    assert (
        cliente.patch(
            f"{RUTA}/NO-EXISTE",
            json={"estado": "INACTIVO"},
            headers=INGENIERO,
        ).status_code
        == 404
    )


def test_modificacion_vacia_o_de_identificadores_se_rechaza(cliente) -> None:
    socio_id = cliente.post(RUTA, json=cuerpo(), headers=INGENIERO).json()["socio_id"]

    assert cliente.patch(f"{RUTA}/{socio_id}", json={}, headers=INGENIERO).status_code == 422
    assert (
        cliente.patch(
            f"{RUTA}/{socio_id}",
            json={"tenant_id": "TENANT-AJENO"},
            headers=INGENIERO,
        ).status_code
        == 422
    )
    assert (
        cliente.patch(
            f"{RUTA}/{socio_id}",
            json={"razon_social": None},
            headers=INGENIERO,
        ).status_code
        == 422
    )
