import pytest
from fastapi.testclient import TestClient

from app.api.socios import obtener_servicio
from app.main import app
from app.socios.dominio.tenant import AprovisionadorTenantsEnMemoria
from app.socios.repositorio import RepositorioSociosEnMemoria
from app.socios.servicio import ServicioSocios
from tests.socios.fabrica import solicitud_alta

RUTA = "/api/v1/socios"
INGENIERO = {"X-Rol": "INGENIERO_INTEGRACIONES"}
CLIENTE = {"X-Rol": "CLIENTE"}


@pytest.fixture
def cliente():
    servicio = ServicioSocios(
        RepositorioSociosEnMemoria(),
        AprovisionadorTenantsEnMemoria(),
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
