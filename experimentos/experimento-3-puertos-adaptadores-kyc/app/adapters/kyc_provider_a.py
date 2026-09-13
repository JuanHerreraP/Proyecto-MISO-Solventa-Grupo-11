"""
Adaptador para el Proveedor KYC simulado A.

Contrato externo simulado del Proveedor A (estilo REST "clásico", en inglés,
campos planos):

    Entrada (lo que el adaptador arma para el proveedor):
        documentType, documentNumber, fullName, birthDate ("YYYY-MM-DD")

    Salida (lo que el proveedor devuelve):
        {
            "verificationId": "...",
            "status": "APPROVED" | "REJECTED" | "PENDING",
            "score": 0-100   # entero, a mayor score, mayor riesgo
        }

Particularidades de este proveedor que el adaptador debe absorber:
- Su estado "PENDING" no es un nombre válido en el dominio de Solventa
  (que usa "IN_REVIEW").
- Su score viene en escala entera 0-100, mientras el dominio usa 0.0-1.0.

El servicio de Identidad (consumidor) nunca ve estos detalles: solo recibe
un `VerificationResult` del dominio.
"""
from __future__ import annotations

import hashlib
from datetime import datetime

from app.domain.models import VerificationRequest, VerificationResult, VerificationStatus
from app.domain.ports import IdentityVerificationProvider


class ProviderAClient:
    """
    Cliente simulado (mock/stub) del Proveedor KYC A. No realiza I/O real:
    para efectos del experimento, representa la llamada HTTP/HTTPS descrita
    en el diseño del experimento (`Proveedor KYC simulado A`).
    """

    def verificar_identidad(
        self, document_type: str, document_number: str, full_name: str, birth_date: str
    ) -> dict:
        # Clasificación determinística a partir del número de documento, para
        # que las pruebas de regresión sean reproducibles sin depender de un
        # proveedor real.
        digest = int(hashlib.sha256(document_number.encode()).hexdigest(), 16)
        bucket = digest % 10

        if bucket < 7:
            status, score = "APPROVED", 15 + (digest % 20)
        elif bucket < 9:
            status, score = "PENDING", 45 + (digest % 20)
        else:
            status, score = "REJECTED", 80 + (digest % 20)

        return {
            "verificationId": f"A-{document_number}-{digest % 100000}",
            "status": status,
            "score": min(score, 100),
        }


class KYCProviderAAdapter(IdentityVerificationProvider):
    """Traduce entre el modelo interno de Solventa y el contrato del Proveedor A."""

    _STATUS_MAP = {
        "APPROVED": VerificationStatus.APPROVED,
        "REJECTED": VerificationStatus.REJECTED,
        "PENDING": VerificationStatus.IN_REVIEW,
    }

    def __init__(self, client: ProviderAClient | None = None):
        self._client = client or ProviderAClient()

    def verify(self, request: VerificationRequest) -> VerificationResult:
        raw = self._client.verificar_identidad(
            document_type=request.document_type,
            document_number=request.document_number,
            full_name=request.full_name,
            birth_date=request.birth_date.isoformat(),
        )
        return VerificationResult(
            verification_id=raw["verificationId"],
            status=self._STATUS_MAP[raw["status"]],
            risk_score=round(raw["score"] / 100, 4),
            provider_name="proveedor-kyc-a",
            checked_at=datetime.utcnow(),
        )
