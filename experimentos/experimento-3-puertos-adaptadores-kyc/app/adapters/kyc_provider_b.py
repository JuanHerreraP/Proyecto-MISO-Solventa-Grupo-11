"""
Adaptador para el Proveedor KYC simulado B.

Contrato externo simulado del Proveedor B (deliberadamente distinto al del
Proveedor A, en español y con estructura anidada):

    Entrada (lo que el adaptador arma para el proveedor):
        {
            "solicitante": {
                "tipoDocumento": "...",
                "numeroDocumento": "...",
                "nombreCompleto": "...",
            },
            "fechaNacimiento": "DD/MM/YYYY",
        }

    Salida (lo que el proveedor devuelve):
        {
            "idVerificacion": "...",
            "resultado": "OK" | "RECHAZADO" | "EN_REVISION",
            "puntajeRiesgo": 0.0-1.0,   # OJO: es un puntaje de CONFIANZA, no de riesgo
        }

Particularidades de este proveedor que el adaptador debe absorber:
- Estructura anidada de la solicitud ("solicitante") en vez de campos planos.
- Fecha en formato DD/MM/YYYY en vez de YYYY-MM-DD.
- Vocabulario de estado distinto y en español ("OK"/"RECHAZADO"/"EN_REVISION").
- Su "puntajeRiesgo" en realidad mide confianza (a mayor valor, MENOR riesgo):
  el adaptador debe invertirlo para que coincida con la semántica de riesgo
  del dominio de Solventa (a mayor risk_score, MAYOR riesgo).

Estas diferencias son intencionales: existen para que el experimento pueda
comprobar que un cambio de proveedor con un contrato genuinamente distinto
queda aislado en el adaptador y no se propaga al servicio de Identidad.
"""
from __future__ import annotations

import hashlib
from datetime import datetime

from app.domain.models import VerificationRequest, VerificationResult, VerificationStatus
from app.domain.ports import IdentityVerificationProvider


class ProviderBClient:
    """
    Cliente simulado (mock/stub) del Proveedor KYC B. No realiza I/O real:
    representa la llamada HTTP/HTTPS descrita en el diseño del experimento
    (`Proveedor KYC simulado B`).
    """

    def evaluar_solicitante(self, solicitante: dict, fecha_nacimiento: str) -> dict:
        digest = int(hashlib.sha256(solicitante["numeroDocumento"].encode()).hexdigest(), 16)
        # Mismos rangos de "bucket" que el Proveedor A para el mismo número de
        # documento, de forma que el experimento pueda comparar el
        # comportamiento observado por el consumidor entre ambos proveedores
        # con los mismos casos de prueba.
        bucket = digest % 10

        if bucket < 7:
            resultado, confianza = "OK", 0.80 + (digest % 20) / 100
        elif bucket < 9:
            resultado, confianza = "EN_REVISION", 0.50 + (digest % 20) / 100
        else:
            resultado, confianza = "RECHAZADO", 0.10 + (digest % 20) / 100

        return {
            "idVerificacion": f"B-{solicitante['numeroDocumento']}-{digest % 100000}",
            "resultado": resultado,
            "puntajeRiesgo": round(min(confianza, 1.0), 4),
        }


class KYCProviderBAdapter(IdentityVerificationProvider):
    """Traduce entre el modelo interno de Solventa y el contrato del Proveedor B."""

    _STATUS_MAP = {
        "OK": VerificationStatus.APPROVED,
        "RECHAZADO": VerificationStatus.REJECTED,
        "EN_REVISION": VerificationStatus.IN_REVIEW,
    }

    def __init__(self, client: ProviderBClient | None = None):
        self._client = client or ProviderBClient()

    def verify(self, request: VerificationRequest) -> VerificationResult:
        raw = self._client.evaluar_solicitante(
            solicitante={
                "tipoDocumento": request.document_type,
                "numeroDocumento": request.document_number,
                "nombreCompleto": request.full_name,
            },
            fecha_nacimiento=request.birth_date.strftime("%d/%m/%Y"),
        )
        # Inversión deliberada: el proveedor entrega "confianza", el dominio
        # de Solventa espera "riesgo".
        riesgo = round(1.0 - raw["puntajeRiesgo"], 4)

        return VerificationResult(
            verification_id=raw["idVerificacion"],
            status=self._STATUS_MAP[raw["resultado"]],
            risk_score=riesgo,
            provider_name="proveedor-kyc-b",
            checked_at=datetime.utcnow(),
        )
