from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.socios import administrador_actual, obtener_servicio
from app.main import app
from app.socios.dominio.auditoria import RepositorioAuditoriaSociosEnMemoria
from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.dominio.tenant import AprovisionadorTenantsEnMemoria
from app.socios.repositorio import RepositorioSociosEnMemoria
from app.socios.servicio import ServicioSocios
from tests.socios.fabrica import solicitud_alta

RUTA = "/api/v1/autorizaciones/socios"
USUARIO_INGENIERO = SimpleNamespace(
    id="ingeniero-01",
    email="ingeniero@solventa.com",
    rol="INGENIERO_INTEGRACIONES",
    activo=True,
)


@pytest.fixture
def cliente_y_socio():
    servicio = ServicioSocios(
        RepositorioSociosEnMemoria(),
        AprovisionadorTenantsEnMemoria(),
        RepositorioAuditoriaSociosEnMemoria(),
    )
    socio = servicio.dar_de_alta(solicitud_alta(), actor_id="ingeniero-01")
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    app.dependency_overrides[administrador_actual] = lambda: USUARIO_INGENIERO
    yield TestClient(app), socio
    app.dependency_overrides.clear()


def headers(socio_id: str, tenant_id: str, scope: str) -> dict[str, str]:
    return {
        "X-Socio-Id": socio_id,
        "X-Tenant-Id": tenant_id,
        "X-Scope": scope,
    }


def test_gateway_autoriza_tenant_y_scope_validos(cliente_y_socio) -> None:
    cliente, socio = cliente_y_socio

    respuesta = cliente.post(
        RUTA,
        headers=headers(
            socio.socio_id,
            socio.tenant_id,
            CodigoEndpoint.COTIZACIONES_CREAR.value,
        ),
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "autorizado": True,
        "socio_id": socio.socio_id,
        "tenant_id": socio.tenant_id,
        "scope": "cotizaciones:crear",
    }


def test_gateway_rechaza_tenant_ajeno(cliente_y_socio) -> None:
    cliente, socio = cliente_y_socio

    respuesta = cliente.post(
        RUTA,
        headers=headers(
            socio.socio_id,
            "TENANT-AJENO",
            CodigoEndpoint.COTIZACIONES_CREAR.value,
        ),
    )

    assert respuesta.status_code == 401


def test_gateway_rechaza_scope_no_autorizado(cliente_y_socio) -> None:
    cliente, socio = cliente_y_socio

    respuesta = cliente.post(
        RUTA,
        headers=headers(
            socio.socio_id,
            socio.tenant_id,
            CodigoEndpoint.POLIZAS_EMITIR.value,
        ),
    )

    assert respuesta.status_code == 403


def test_gateway_rechaza_scope_inexistente(cliente_y_socio) -> None:
    cliente, socio = cliente_y_socio

    respuesta = cliente.post(
        RUTA,
        headers=headers(socio.socio_id, socio.tenant_id, "socios:administrar"),
    )

    assert respuesta.status_code == 403


def test_gateway_rechaza_socio_inactivo(cliente_y_socio) -> None:
    cliente, socio = cliente_y_socio
    cliente.patch(
        f"/api/v1/socios/{socio.socio_id}",
        json={"estado": "INACTIVO"},
    )

    respuesta = cliente.post(
        RUTA,
        headers=headers(
            socio.socio_id,
            socio.tenant_id,
            CodigoEndpoint.COTIZACIONES_CREAR.value,
        ),
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == "El socio no se encuentra activo."


def test_gateway_rechaza_credenciales_incompletas(cliente_y_socio) -> None:
    cliente, _ = cliente_y_socio

    assert cliente.post(RUTA).status_code == 401
