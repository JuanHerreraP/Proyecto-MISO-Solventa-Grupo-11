"""
Pruebas unitarias del adaptador del Proveedor B: verifican que las
particularidades del contrato externo (estado "PENDING", score 0-100) se
traducen correctamente al modelo de dominio, y que esa traducción vive
únicamente dentro del adaptador.
"""
from datetime import date

from app.identidad.adaptadores.kyc_provider_b import KYCProviderBAdapter, ProviderBClient
from app.identidad.modelos import VerificationRequest, VerificationStatus


class FakeProviderBClient(ProviderBClient):
    def __init__(self, response: dict):
        self._response = response

    def verificar_identidad(self, document_type, document_number, full_name, birth_date):
        return self._response


def _request(document_number: str = "123") -> VerificationRequest:
    return VerificationRequest(
        customer_id="c1",
        consent_id="k1",
        document_type="CC",
        document_number=document_number,
        full_name="Ana Pérez",
        birth_date=date(1995, 1, 1),
    )


def test_traduce_pending_b_in_review_y_normaliza_el_score():
    fake = FakeProviderBClient({"verificationId": "B-FAKE-1", "status": "PENDING", "score": 55})
    adapter = KYCProviderBAdapter(client=fake)

    result = adapter.verify(_request())

    assert result.status == VerificationStatus.IN_REVIEW
    assert result.risk_score == 0.55
    assert result.provider_name == "proveedor-kyc-b"
    assert result.verification_id == "B-FAKE-1"


def test_traduce_approved_y_rejected_correctamente():
    fake_aprobado = FakeProviderBClient({"verificationId": "B-1", "status": "APPROVED", "score": 10})
    fake_rechazado = FakeProviderBClient({"verificationId": "B-2", "status": "REJECTED", "score": 90})

    aprobado = KYCProviderBAdapter(client=fake_aprobado).verify(_request())
    rechazado = KYCProviderBAdapter(client=fake_rechazado).verify(_request())

    assert aprobado.status == VerificationStatus.APPROVED
    assert rechazado.status == VerificationStatus.REJECTED
