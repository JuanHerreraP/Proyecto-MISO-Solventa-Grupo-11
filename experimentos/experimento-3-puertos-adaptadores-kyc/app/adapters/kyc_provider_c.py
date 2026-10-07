"""
Adaptador para el Proveedor KYC simulado C.

Contrato externo deliberadamente distinto:

Entrada:
{
    "identificacion": {
        "tipo": "...",
        "numero": "..."
    },
    "persona": {
        "nombre": "...",
        "fechaNacimiento": "YYYYMMDD"
    }
}

Salida:
{
    "referencia": "...",
    "decision": "CLEAR" | "BLOCK" | "MANUAL_CHECK",
    "bandaRiesgo": "LOW" | "MEDIUM" | "HIGH"
}
"""
from __future__ import annotations

import hashlib
from datetime import datetime

from app.domain.models import VerificationRequest, VerificationResult, VerificationStatus
from app.domain.ports import IdentityVerificationProvider


class ProviderCClient:
    """Cliente simulado del Proveedor KYC C."""

    def consultar_identidad(self, payload: dict) -> dict:
        document_number = payload["identificacion"]["numero"]
        digest = int(hashlib.sha256(document_number.encode()).hexdigest(), 16)
        bucket = digest % 10

        if bucket < 7:
            decision, risk_band = "CLEAR", "LOW"
        elif bucket < 9:
            decision, risk_band = "MANUAL_CHECK", "MEDIUM"
        else:
            decision, risk_band = "BLOCK", "HIGH"

        return {
            "referencia": f"C-{document_number}-{digest % 100000}",
            "decision": decision,
            "bandaRiesgo": risk_band,
        }


class KYCProviderCAdapter(IdentityVerificationProvider):
    """Traduce el contrato del Proveedor C al modelo de dominio de Solventa."""

    _STATUS_MAP = {
        "CLEAR": VerificationStatus.APPROVED,
        "BLOCK": VerificationStatus.REJECTED,
        "MANUAL_CHECK": VerificationStatus.IN_REVIEW,
    }

    _RISK_MAP = {
        "LOW": 0.20,
        "MEDIUM": 0.60,
        "HIGH": 0.90,
    }

    def __init__(self, client: ProviderCClient | None = None):
        self._client = client or ProviderCClient()

    def verify(self, request: VerificationRequest) -> VerificationResult:
        payload = {
            "identificacion": {
                "tipo": request.document_type,
                "numero": request.document_number,
            },
            "persona": {
                "nombre": request.full_name,
                "fechaNacimiento": request.birth_date.strftime("%Y%m%d"),
            },
        }

        raw = self._client.consultar_identidad(payload)

        return VerificationResult(
            verification_id=raw["referencia"],
            status=self._STATUS_MAP[raw["decision"]],
            risk_score=self._RISK_MAP[raw["bandaRiesgo"]],
            provider_name="proveedor-kyc-c",
            checked_at=datetime.utcnow(),
        )