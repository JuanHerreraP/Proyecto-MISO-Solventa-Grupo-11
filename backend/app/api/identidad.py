from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.identidad.config import (
    get_configured_provider_name,
    get_identity_verification_provider,
)
from app.identidad.modelos import VerificationRequest
from app.identidad.puertos import IdentityVerificationProvider

router = APIRouter(
    prefix="/identidad",
    tags=["Identidad"],
)


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


@router.post(
    "/verificaciones",
    response_model=VerificacionIdentidadResponse,
)
def verificar_identidad(
    payload: VerificacionIdentidadRequest,
    provider: IdentityVerificationProvider = Depends(get_identity_verification_provider),
):
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


@router.get("/salud")
def salud_identidad():
    return {
        "status": "ok",
        "proveedor_kyc_activo": get_configured_provider_name(),
    }
