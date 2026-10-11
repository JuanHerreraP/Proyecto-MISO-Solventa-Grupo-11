"""Adaptador para el Proveedor KYC A."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx

from app.identidad.modelos import (
    VerificationRequest,
    VerificationResult,
    VerificationStatus,
)
from app.identidad.puertos import IdentityVerificationProvider


class ProviderAClient:
    """Cliente HTTP del proveedor KYC A."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 3.0,
    ):
        self._base_url = base_url or os.getenv(
            "KYC_PROVIDER_A_URL",
            "http://127.0.0.1:8001",
        )

        self._timeout = timeout

    def verificar_identidad(
        self,
        document_type: str,
        document_number: str,
        full_name: str,
        birth_date: str,
    ) -> dict:

        response = httpx.post(
            f"{self._base_url}/kyc/verify",
            json={
                "documentType": document_type,
                "documentNumber": document_number,
                "fullName": full_name,
                "birthDate": birth_date,
            },
            timeout=self._timeout,
        )

        response.raise_for_status()

        return response.json()


class KYCProviderAAdapter(IdentityVerificationProvider):
    """Traduce el contrato de Provider A al dominio Solventa."""

    _STATUS_MAP = {
        "APPROVED": VerificationStatus.APPROVED,
        "REJECTED": VerificationStatus.REJECTED,
        "PENDING": VerificationStatus.IN_REVIEW,
    }

    def __init__(
        self,
        client: ProviderAClient | None = None,
    ):
        self._client = client or ProviderAClient()

    def verify(
        self,
        request: VerificationRequest,
    ) -> VerificationResult:

        raw = self._client.verificar_identidad(
            document_type=request.document_type,
            document_number=request.document_number,
            full_name=request.full_name,
            birth_date=request.birth_date.isoformat(),
        )

        return VerificationResult(
            verification_id=raw["verificationId"],
            status=self._STATUS_MAP[raw["status"]],
            risk_score=round(
                raw["score"] / 100,
                4,
            ),
            provider_name="proveedor-kyc-a",
            checked_at=datetime.now(timezone.utc),
        )