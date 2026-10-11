import os

from app.identidad.adaptadores.kyc_provider_a import (
    KYCProviderAAdapter,
)
from app.identidad.adaptadores.kyc_provider_b import (
    KYCProviderBAdapter,
)
from app.identidad.adaptadores.kyc_provider_c import (
    KYCProviderCAdapter,
)
from app.identidad.puertos import IdentityVerificationProvider


def get_configured_provider_name() -> str:
    return os.getenv(
        "KYC_PROVIDER",
        "A",
    ).strip().upper()


def get_identity_verification_provider(
) -> IdentityVerificationProvider:

    provider_name = get_configured_provider_name()

    if provider_name == "A":
        return KYCProviderAAdapter()

    if provider_name == "B":
        return KYCProviderBAdapter()

    if provider_name == "C":
        return KYCProviderCAdapter()

    raise ValueError(
        f"Proveedor KYC no soportado: {provider_name}"
    )