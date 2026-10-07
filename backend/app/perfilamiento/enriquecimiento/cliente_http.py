"""Cliente HTTP compartido para las integraciones con proveedores externos (EC07).

- Solo acepta URL `https://`, salvo que se permita HTTP de forma explícita para desarrollo.
- Exige TLS 1.2 o superior y valida el certificado del proveedor.
- Autentica cada solicitud con un token de portador.
"""

import ssl

import httpx

TIEMPO_LIMITE_SEGUNDOS = 0.25


class ConfiguracionInsegura(Exception):
    """La configuración de la integración no cumple los requisitos de seguridad."""


def contexto_tls() -> ssl.SSLContext:
    contexto = ssl.create_default_context()
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2
    return contexto


def crear_cliente(
    url_base: str,
    token: str,
    *,
    tiempo_limite: float = TIEMPO_LIMITE_SEGUNDOS,
    permitir_http: bool = False,
    transporte: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    if not token:
        raise ConfiguracionInsegura("La integración requiere un token de autenticación.")
    if not url_base.startswith("https://") and not (
        permitir_http and url_base.startswith("http://")
    ):
        raise ConfiguracionInsegura("La integración requiere una URL https://.")

    return httpx.AsyncClient(
        base_url=url_base,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=httpx.Timeout(tiempo_limite),
        limits=httpx.Limits(max_keepalive_connections=50, max_connections=200),
        verify=contexto_tls(),
        transport=transporte,
    )
