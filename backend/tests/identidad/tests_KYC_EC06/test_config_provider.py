"""Pruebas de configuración y selección de proveedores KYC.

Estas pruebas verifican que la implementación concreta del puerto
IdentityVerificationProvider pueda sustituirse mediante configuración,
sin modificar el consumidor del servicio.
"""

import pytest

from app.identidad.adaptadores.kyc_provider_a import KYCProviderAAdapter
from app.identidad.adaptadores.kyc_provider_b import KYCProviderBAdapter
from app.identidad.adaptadores.kyc_provider_c import KYCProviderCAdapter
from app.identidad.config import (
    get_configured_provider_name,
    get_identity_verification_provider,
)


@pytest.mark.parametrize(
    "provider_name,expected_type",
    [
        ("A", KYCProviderAAdapter),
        ("B", KYCProviderBAdapter),
        ("C", KYCProviderCAdapter),
    ],
)
def test_selecciona_el_adaptador_configurado(
    monkeypatch,
    provider_name,
    expected_type,
):
    monkeypatch.setenv(
        "KYC_PROVIDER",
        provider_name,
    )

    provider = get_identity_verification_provider()

    assert isinstance(
        provider,
        expected_type,
    )


def test_provider_a_es_el_proveedor_por_defecto(monkeypatch):
    monkeypatch.delenv(
        "KYC_PROVIDER",
        raising=False,
    )

    assert get_configured_provider_name() == "A"

    provider = get_identity_verification_provider()

    assert isinstance(
        provider,
        KYCProviderAAdapter,
    )


@pytest.mark.parametrize(
    "valor_configurado,valor_esperado",
    [
        ("a", "A"),
        ("b", "B"),
        ("c", "C"),
        (" A ", "A"),
        (" b ", "B"),
        (" C ", "C"),
    ],
)
def test_normaliza_el_nombre_del_proveedor(
    monkeypatch,
    valor_configurado,
    valor_esperado,
):
    monkeypatch.setenv(
        "KYC_PROVIDER",
        valor_configurado,
    )

    assert (
        get_configured_provider_name()
        == valor_esperado
    )


def test_proveedor_no_soportado_genera_error(monkeypatch):
    monkeypatch.setenv(
        "KYC_PROVIDER",
        "X",
    )

    with pytest.raises(
        ValueError,
        match="Proveedor KYC no soportado",
    ):
        get_identity_verification_provider()