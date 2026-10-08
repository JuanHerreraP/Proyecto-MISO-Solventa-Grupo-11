from datetime import datetime, timezone

import pytest

from app.socios.dominio.modelos import EstadoSocio
from app.socios.dominio.tenant import AprovisionadorTenantsEnMemoria
from app.socios.repositorio import RepositorioSociosEnMemoria
from app.socios.servicio import NitDuplicado, ServicioSocios
from tests.socios.fabrica import solicitud_alta

FECHA = datetime(2026, 10, 7, tzinfo=timezone.utc)


def crear_servicio() -> tuple[
    ServicioSocios,
    RepositorioSociosEnMemoria,
    AprovisionadorTenantsEnMemoria,
]:
    repositorio = RepositorioSociosEnMemoria()
    tenants = AprovisionadorTenantsEnMemoria(generar_id=lambda: "TENANT-001")
    servicio = ServicioSocios(
        repositorio=repositorio,
        tenants=tenants,
        generar_id=lambda: "SOCIO-001",
        reloj=lambda: FECHA,
    )
    return servicio, repositorio, tenants


def test_alta_aprovisiona_tenant_activa_y_guarda_el_socio() -> None:
    servicio, repositorio, tenants = crear_servicio()

    socio = servicio.dar_de_alta(solicitud_alta())

    assert socio.socio_id == "SOCIO-001"
    assert socio.tenant_id == "TENANT-001"
    assert socio.estado is EstadoSocio.ACTIVO
    assert repositorio.obtener_por_nit(socio.nit) == socio
    assert tenants.obtener_por_socio(socio.socio_id).tenant_id == socio.tenant_id


def test_rechaza_un_nit_duplicado_sin_crear_otro_tenant() -> None:
    servicio, _, tenants = crear_servicio()
    servicio.dar_de_alta(solicitud_alta())

    with pytest.raises(NitDuplicado):
        servicio.dar_de_alta(solicitud_alta())

    assert tenants.obtener_por_socio("SOCIO-001") is not None
