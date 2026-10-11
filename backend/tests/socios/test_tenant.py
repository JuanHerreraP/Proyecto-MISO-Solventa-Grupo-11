from datetime import datetime, timezone

from app.socios.dominio.tenant import AprovisionadorTenantsEnMemoria


def test_aprovisiona_un_tenant_logico_para_el_socio() -> None:
    tenants = AprovisionadorTenantsEnMemoria(generar_id=lambda: "TENANT-001")
    fecha = datetime(2026, 10, 7, tzinfo=timezone.utc)

    tenant = tenants.aprovisionar("SOCIO-001", fecha)

    assert tenant.tenant_id == "TENANT-001"
    assert tenant.socio_id == "SOCIO-001"
    assert tenants.obtener_por_socio("SOCIO-001") == tenant


def test_reintentar_aprovisionamiento_no_duplica_el_tenant() -> None:
    tenants = AprovisionadorTenantsEnMemoria(generar_id=lambda: "TENANT-001")
    fecha = datetime(2026, 10, 7, tzinfo=timezone.utc)

    primero = tenants.aprovisionar("SOCIO-001", fecha)
    segundo = tenants.aprovisionar("SOCIO-001", fecha)

    assert segundo == primero
