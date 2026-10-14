from datetime import datetime, timezone

import jwt

from app.identidad.tokens import PUBLIC_KEY_PATH
from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.dominio.credenciales import CredencialesSocio
from app.socios.tokens import crear_access_token_socio


def test_token_incluye_identidad_tenant_scopes_y_expiracion() -> None:
    credenciales = CredencialesSocio(
        socio_id="SOCIO-001",
        tenant_id="TENANT-001",
        client_id="solv_cliente_001",
        secret_hash="hash-seguro",
        scopes={CodigoEndpoint.COTIZACIONES_CREAR},
        creado_en=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )

    token, expires_in = crear_access_token_socio(
        credenciales,
        {CodigoEndpoint.COTIZACIONES_CREAR},
    )
    payload = jwt.decode(
        token,
        PUBLIC_KEY_PATH.read_text(),
        algorithms=["RS256"],
    )

    assert payload["sub"] == "solv_cliente_001"
    assert payload["socio_id"] == "SOCIO-001"
    assert payload["tenant_id"] == "TENANT-001"
    assert payload["scope"] == ["cotizaciones:crear"]
    assert payload["type"] == "partner_access"
    assert payload["exp"] - payload["iat"] == 900
    assert expires_in == 900
