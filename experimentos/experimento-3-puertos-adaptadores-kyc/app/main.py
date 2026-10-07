"""
Servicio de Identidad, KYC y Consentimiento (consumidor del puerto), expuesto
como una API mínima para efectos del experimento.

IMPORTANTE para la lectura del experimento: este módulo es el "consumidor"
cuya estabilidad frente al cambio de proveedor KYC es exactamente lo que se
está poniendo a prueba. Fíjense en que en ningún punto de este archivo se
importa `KYCProviderAAdapter` ni `KYCProviderBAdapter` directamente desde el
endpoint: la única función que conoce esos nombres es
`get_identity_verification_provider`, que actúa como el punto único de
ensamblaje (composition root) del servicio.
"""
from datetime import date

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app.adapters.kyc_provider_a import KYCProviderAAdapter
from app.adapters.kyc_provider_b import KYCProviderBAdapter
from app.adapters.kyc_provider_c import KYCProviderCAdapter
from app.config import get_configured_provider_name
from app.domain.models import VerificationRequest
from app.domain.ports import IdentityVerificationProvider

app = FastAPI(title="Identidad, KYC y Consentimiento — Experimento Puertos y Adaptadores")


def get_identity_verification_provider() -> IdentityVerificationProvider:
    """
    Único lugar del servicio que sabe que existen un "Proveedor A" y un
    "Proveedor B". Si mañana se agrega un Proveedor C, el cambio se hace acá
    y en un nuevo adaptador — nunca en el endpoint de abajo.
    """
    provider_name = get_configured_provider_name()
    if provider_name == "A":
        return KYCProviderAAdapter()
    if provider_name == "B":
        return KYCProviderBAdapter()
    if provider_name == "C":
        return KYCProviderCAdapter()
    raise ValueError(f"Proveedor KYC no soportado: {provider_name}")


class VerificacionIdentidadRequest(BaseModel):
    customer_id: str
    consent_id: str
    document_type: str
    document_number: str
    full_name: str
    birth_date: date


class VerificacionIdentidadResponse(BaseModel):
    verification_id: str
    status: str
    risk_score: float
    checked_at: str


@app.post("/identidad/verificaciones", response_model=VerificacionIdentidadResponse)
def verificar_identidad(
    payload: VerificacionIdentidadRequest,
    provider: IdentityVerificationProvider = Depends(get_identity_verification_provider),
) -> VerificacionIdentidadResponse:
    request = VerificationRequest(
        customer_id=payload.customer_id,
        consent_id=payload.consent_id,
        document_type=payload.document_type,
        document_number=payload.document_number,
        full_name=payload.full_name,
        birth_date=payload.birth_date,
    )
    result = provider.verify(request)
    return VerificacionIdentidadResponse(
        verification_id=result.verification_id,
        status=result.status.value,
        risk_score=result.risk_score,
        checked_at=result.checked_at.isoformat(),
    )


@app.get("/salud")
def salud() -> dict:
    return {"status": "ok", "proveedor_kyc_activo": get_configured_provider_name()}
