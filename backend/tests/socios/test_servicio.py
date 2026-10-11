from datetime import datetime, timezone

import pytest

from app.socios.dominio.auditoria import (
    AccionAuditoria,
    RepositorioAuditoriaSociosEnMemoria,
)
from app.socios.dominio.modelos import EstadoSocio, SolicitudActualizacionSocio
from app.socios.dominio.tenant import AprovisionadorTenantsEnMemoria
from app.socios.repositorio import RepositorioSociosEnMemoria
from app.socios.servicio import NitDuplicado, ServicioSocios
from tests.socios.fabrica import solicitud_alta

FECHA = datetime(2026, 10, 7, tzinfo=timezone.utc)


def crear_servicio() -> tuple[
    ServicioSocios,
    RepositorioSociosEnMemoria,
    AprovisionadorTenantsEnMemoria,
    RepositorioAuditoriaSociosEnMemoria,
]:
    repositorio = RepositorioSociosEnMemoria()
    tenants = AprovisionadorTenantsEnMemoria(generar_id=lambda: "TENANT-001")
    auditoria = RepositorioAuditoriaSociosEnMemoria()
    servicio = ServicioSocios(
        repositorio=repositorio,
        tenants=tenants,
        auditoria=auditoria,
        generar_id=lambda: "SOCIO-001",
        reloj=lambda: FECHA,
    )
    return servicio, repositorio, tenants, auditoria


def test_alta_aprovisiona_tenant_activa_y_guarda_el_socio() -> None:
    servicio, repositorio, tenants, _ = crear_servicio()

    socio = servicio.dar_de_alta(solicitud_alta(), actor_id="ingeniero-01")

    assert socio.socio_id == "SOCIO-001"
    assert socio.tenant_id == "TENANT-001"
    assert socio.estado is EstadoSocio.ACTIVO
    assert repositorio.obtener_por_nit(socio.nit) == socio
    assert tenants.obtener_por_socio(socio.socio_id).tenant_id == socio.tenant_id


def test_rechaza_un_nit_duplicado_sin_crear_otro_tenant() -> None:
    servicio, _, tenants, _ = crear_servicio()
    servicio.dar_de_alta(solicitud_alta(), actor_id="ingeniero-01")

    with pytest.raises(NitDuplicado):
        servicio.dar_de_alta(solicitud_alta(), actor_id="ingeniero-01")

    assert tenants.obtener_por_socio("SOCIO-001") is not None


def test_consulta_y_actualiza_la_configuracion_sin_cambiar_identificadores() -> None:
    servicio, _, _, _ = crear_servicio()
    creado = servicio.dar_de_alta(solicitud_alta(), actor_id="ingeniero-01")

    actualizado = servicio.actualizar(
        creado.socio_id,
        SolicitudActualizacionSocio(razon_social="Banco Andes Digital S.A."),
        actor_id="ingeniero-02",
    )

    assert servicio.consultar(creado.socio_id) == actualizado
    assert actualizado.razon_social == "Banco Andes Digital S.A."
    assert actualizado.nit == creado.nit
    assert actualizado.tenant_id == creado.tenant_id


def test_registra_auditoria_del_alta_y_la_modificacion() -> None:
    servicio, _, _, _ = crear_servicio()
    socio = servicio.dar_de_alta(solicitud_alta(), actor_id="ingeniero-01")
    servicio.actualizar(
        socio.socio_id,
        SolicitudActualizacionSocio(estado=EstadoSocio.INACTIVO),
        actor_id="ingeniero-02",
    )

    registros = servicio.consultar_auditoria(socio.socio_id)

    assert [registro.accion for registro in registros] == [
        AccionAuditoria.ALTA,
        AccionAuditoria.MODIFICACION,
    ]
    assert registros[0].actor_id == "ingeniero-01"
    assert registros[1].actor_id == "ingeniero-02"
    assert registros[1].campos_modificados == ["estado"]
