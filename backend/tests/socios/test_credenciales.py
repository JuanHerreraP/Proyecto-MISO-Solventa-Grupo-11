from datetime import datetime, timezone

from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.dominio.credenciales import (
    generar_credenciales,
    verificar_secret,
)


def test_genera_client_id_y_secreto_sin_guardar_el_secreto_plano() -> None:
    fecha = datetime.now(timezone.utc)

    credenciales, client_secret = generar_credenciales(
        socio_id="SOCIO-001",
        tenant_id="TENANT-001",
        scopes={CodigoEndpoint.COTIZACIONES_CREAR},
        creado_en=fecha,
    )

    assert credenciales.client_id.startswith("solv_")
    assert client_secret.startswith("solv_secret_")
    assert credenciales.secret_hash != client_secret
    assert credenciales.socio_id == "SOCIO-001"
    assert credenciales.tenant_id == "TENANT-001"


def test_verifica_el_secreto_correcto() -> None:
    credenciales, client_secret = generar_credenciales(
        socio_id="SOCIO-001",
        tenant_id="TENANT-001",
        scopes={CodigoEndpoint.COTIZACIONES_CREAR},
        creado_en=datetime.now(timezone.utc),
    )

    assert verificar_secret(client_secret, credenciales)


def test_rechaza_un_secreto_incorrecto() -> None:
    credenciales, _ = generar_credenciales(
        socio_id="SOCIO-001",
        tenant_id="TENANT-001",
        scopes={CodigoEndpoint.COTIZACIONES_CREAR},
        creado_en=datetime.now(timezone.utc),
    )

    assert not verificar_secret("secreto-incorrecto", credenciales)
