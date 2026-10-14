from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.credenciales_socios import obtener_servicio_credenciales
from app.api.socios import administrador_actual
from app.main import app
from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.dominio.credenciales import CredencialesSocio
from app.socios.dominio.modelos import EstadoSocio, SocioDistribucion
from app.socios.repositorio import RepositorioSociosEnMemoria
from app.socios.repositorio_credenciales import RepositorioCredencialesSociosEnMemoria
from app.socios.servicio_credenciales import ServicioCredencialesSocios
from tests.socios.fabrica import solicitud_alta

FECHA = datetime(2026, 10, 13, tzinfo=timezone.utc)
USUARIO_INGENIERO = SimpleNamespace(
    id="ingeniero-01",
    email="ingeniero@solventa.com",
    rol="INGENIERO_INTEGRACIONES",
    activo=True,
)


def generar_credenciales_fijas(
    socio_id: str,
    tenant_id: str,
    scopes: set[CodigoEndpoint],
    creado_en: datetime,
) -> tuple[CredencialesSocio, str]:
    return (
        CredencialesSocio(
            socio_id=socio_id,
            tenant_id=tenant_id,
            client_id="solv_cliente_001",
            secret_hash="hash-seguro",
            scopes=scopes,
            creado_en=creado_en,
        ),
        "solv_secret_una_sola_vez",
    )


def crear_socio(estado: EstadoSocio = EstadoSocio.ACTIVO) -> SocioDistribucion:
    return SocioDistribucion(
        **solicitud_alta().model_dump(),
        socio_id="SOCIO-001",
        tenant_id="TENANT-001",
        estado=estado,
        creado_en=FECHA,
        actualizado_en=FECHA,
    )


def configurar_api(
    socio: SocioDistribucion | None,
) -> tuple[TestClient, RepositorioCredencialesSociosEnMemoria]:
    socios = RepositorioSociosEnMemoria()
    credenciales = RepositorioCredencialesSociosEnMemoria()
    if socio is not None:
        socios.guardar(socio)
    servicio = ServicioCredencialesSocios(
        socios=socios,
        credenciales=credenciales,
        reloj=lambda: FECHA,
        generador=generar_credenciales_fijas,
    )
    app.dependency_overrides[obtener_servicio_credenciales] = lambda: servicio
    app.dependency_overrides[administrador_actual] = lambda: USUARIO_INGENIERO
    return TestClient(app), credenciales


def limpiar_api() -> None:
    app.dependency_overrides.clear()


def test_endpoint_aprovisiona_y_entrega_el_secreto_una_sola_vez() -> None:
    cliente, repositorio = configurar_api(crear_socio())
    try:
        respuesta = cliente.post("/api/v1/socios/SOCIO-001/credenciales")
    finally:
        limpiar_api()

    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "socio_id": "SOCIO-001",
        "tenant_id": "TENANT-001",
        "client_id": "solv_cliente_001",
        "client_secret": "solv_secret_una_sola_vez",
        "scopes": ["cotizaciones:crear"],
        "creado_en": "2026-10-13T00:00:00Z",
    }
    assert "secret_hash" not in respuesta.json()
    persistidas = repositorio.obtener_por_client_id("solv_cliente_001")
    assert persistidas is not None
    assert persistidas.secret_hash == "hash-seguro"


def test_endpoint_rechaza_un_socio_inexistente() -> None:
    cliente, _ = configurar_api(None)
    try:
        respuesta = cliente.post("/api/v1/socios/SOCIO-INEXISTENTE/credenciales")
    finally:
        limpiar_api()

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "El socio no existe."


def test_endpoint_rechaza_un_socio_inactivo() -> None:
    cliente, _ = configurar_api(crear_socio(EstadoSocio.INACTIVO))
    try:
        respuesta = cliente.post("/api/v1/socios/SOCIO-001/credenciales")
    finally:
        limpiar_api()

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == ("El socio debe estar activo para generar credenciales.")
