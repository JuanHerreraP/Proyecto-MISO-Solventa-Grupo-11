from datetime import datetime, timezone

import pytest

from app.socios.dominio.auditoria import RepositorioAuditoriaSociosEnMemoria
from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.dominio.modelos import EstadoSocio, SolicitudActualizacionSocio
from app.socios.dominio.tenant import AprovisionadorTenantsEnMemoria
from app.socios.repositorio import RepositorioSociosEnMemoria
from app.socios.servicio import (
    CredencialesSocioInvalidas,
    EndpointNoAutorizado,
    ServicioSocios,
    SocioInactivo,
)
from tests.socios.fabrica import solicitud_alta

FECHA = datetime(2026, 10, 7, tzinfo=timezone.utc)


def servicio_con_dos_socios() -> tuple[ServicioSocios, object, object]:
    ids_socios = iter(["SOCIO-A", "SOCIO-B"])
    ids_tenants = iter(["TENANT-A", "TENANT-B"])
    servicio = ServicioSocios(
        repositorio=RepositorioSociosEnMemoria(),
        tenants=AprovisionadorTenantsEnMemoria(generar_id=lambda: next(ids_tenants)),
        auditoria=RepositorioAuditoriaSociosEnMemoria(),
        generar_id=lambda: next(ids_socios),
        reloj=lambda: FECHA,
    )
    socio_a = servicio.dar_de_alta(
        solicitud_alta(endpoints_autorizados={CodigoEndpoint.COTIZACIONES_CREAR}),
        actor_id="ingeniero-01",
    )
    socio_b = servicio.dar_de_alta(
        solicitud_alta(
            nit="900987654-3",
            razon_social="Aerolínea Norte S.A.",
            endpoints_autorizados={CodigoEndpoint.POLIZAS_EMITIR},
        ),
        actor_id="ingeniero-01",
    )
    return servicio, socio_a, socio_b


def test_autoriza_scope_configurado_en_el_tenant_del_socio() -> None:
    servicio, socio_a, _ = servicio_con_dos_socios()

    autorizado = servicio.autorizar_consumo(
        socio_a.socio_id,
        socio_a.tenant_id,
        CodigoEndpoint.COTIZACIONES_CREAR,
    )

    assert autorizado == socio_a


def test_impide_usar_el_tenant_de_otro_socio() -> None:
    servicio, socio_a, socio_b = servicio_con_dos_socios()

    with pytest.raises(CredencialesSocioInvalidas):
        servicio.autorizar_consumo(
            socio_a.socio_id,
            socio_b.tenant_id,
            CodigoEndpoint.COTIZACIONES_CREAR,
        )


def test_impide_consumir_un_scope_no_asignado() -> None:
    servicio, socio_a, _ = servicio_con_dos_socios()

    with pytest.raises(EndpointNoAutorizado):
        servicio.autorizar_consumo(
            socio_a.socio_id,
            socio_a.tenant_id,
            CodigoEndpoint.POLIZAS_EMITIR,
        )


def test_impide_consumir_apis_a_un_socio_inactivo() -> None:
    servicio, socio_a, _ = servicio_con_dos_socios()
    servicio.actualizar(
        socio_a.socio_id,
        SolicitudActualizacionSocio(estado=EstadoSocio.INACTIVO),
        actor_id="ingeniero-01",
    )

    with pytest.raises(SocioInactivo):
        servicio.autorizar_consumo(
            socio_a.socio_id,
            socio_a.tenant_id,
            CodigoEndpoint.COTIZACIONES_CREAR,
        )
