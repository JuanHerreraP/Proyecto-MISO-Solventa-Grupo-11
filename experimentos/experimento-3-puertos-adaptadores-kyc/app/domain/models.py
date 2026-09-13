"""
Modelo de dominio, agnóstico de proveedor, para la verificación de identidad.

Estos tipos son el "idioma común" de Solventa: tanto el servicio de Identidad
(consumidor) como cualquier adaptador de proveedor KYC (Proveedor A, Proveedor B,
o uno futuro) deben hablarlo. Ningún campo aquí debe reflejar el contrato
particular de un proveedor externo.
"""
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class VerificationStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IN_REVIEW = "IN_REVIEW"


@dataclass(frozen=True)
class VerificationRequest:
    customer_id: str
    consent_id: str
    document_type: str
    document_number: str
    full_name: str
    birth_date: date


@dataclass(frozen=True)
class VerificationResult:
    verification_id: str
    status: VerificationStatus
    # Riesgo normalizado 0.0 (bajo riesgo) - 1.0 (alto riesgo). La semántica de
    # "riesgo" (y no de "confianza" o "score" crudo del proveedor) es una
    # decisión del dominio: cada adaptador debe traducir a esta semántica.
    risk_score: float
    provider_name: str
    checked_at: datetime
