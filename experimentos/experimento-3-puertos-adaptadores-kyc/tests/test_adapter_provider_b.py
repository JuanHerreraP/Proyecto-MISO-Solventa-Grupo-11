"""
Pruebas unitarias del adaptador del Proveedor B: verifican que su contrato
(estructura anidada, vocabulario en español, y la inversión confianza <->
riesgo) se traduce correctamente al modelo de dominio, y que esa traducción
vive únicamente dentro del adaptador.
"""
from datetime import date

from app.adapters.kyc_provider_b import KYCProviderBAdapter, ProviderBClient
from app.domain.models import VerificationRequest, VerificationStatus


class FakeProviderBClient(ProviderBClient):
    def __init__(self, response: dict):
        self._response = response

    def evaluar_solicitante(self, solicitante, fecha_nacimiento):
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


def test_traduce_en_revision_e_invierte_la_semantica_de_riesgo():
    fake = FakeProviderBClient(
        {"idVerificacion": "B-FAKE-1", "resultado": "EN_REVISION", "puntajeRiesgo": 0.60}
    )
    adapter = KYCProviderBAdapter(client=fake)

    result = adapter.verify(_request())

    assert result.status == VerificationStatus.IN_REVIEW
    # El proveedor entrega 0.60 de "confianza"; el dominio espera "riesgo" => 1 - 0.60
    assert result.risk_score == 0.40
    assert result.provider_name == "proveedor-kyc-b"
    assert result.verification_id == "B-FAKE-1"


def test_traduce_ok_y_rechazado_correctamente():
    fake_ok = FakeProviderBClient({"idVerificacion": "B-1", "resultado": "OK", "puntajeRiesgo": 0.9})
    fake_rechazado = FakeProviderBClient(
        {"idVerificacion": "B-2", "resultado": "RECHAZADO", "puntajeRiesgo": 0.1}
    )

    ok = KYCProviderBAdapter(client=fake_ok).verify(_request())
    rechazado = KYCProviderBAdapter(client=fake_rechazado).verify(_request())

    assert ok.status == VerificationStatus.APPROVED
    assert rechazado.status == VerificationStatus.REJECTED
