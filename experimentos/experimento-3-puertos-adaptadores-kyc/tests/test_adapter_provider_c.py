"""
Pruebas unitarias del adaptador del Proveedor C: verifican que su contrato
(estructura de identificación y persona, vocabulario CLEAR/BLOCK/MANUAL_CHECK
y bandas de riesgo LOW/MEDIUM/HIGH) se traduce correctamente al modelo de
dominio, y que esa traducción vive únicamente dentro del adaptador.
"""

from datetime import date

from app.adapters.kyc_provider_c import KYCProviderCAdapter, ProviderCClient
from app.domain.models import VerificationRequest, VerificationStatus


class FakeProviderCClient(ProviderCClient):
    def __init__(self, response: dict):
        self._response = response
        self.last_payload = None

    def consultar_identidad(self, payload: dict) -> dict:
        self.last_payload = payload
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


def test_traduce_manual_check_y_construye_el_contrato_del_proveedor_c():
    fake = FakeProviderCClient(
        {
            "referencia": "C-FAKE-1",
            "decision": "MANUAL_CHECK",
            "bandaRiesgo": "MEDIUM",
        }
    )

    adapter = KYCProviderCAdapter(client=fake)
    result = adapter.verify(_request())

    assert fake.last_payload == {
        "identificacion": {
            "tipo": "CC",
            "numero": "123",
        },
        "persona": {
            "nombre": "Ana Pérez",
            "fechaNacimiento": "19950101",
        },
    }

    assert result.verification_id == "C-FAKE-1"
    assert result.status == VerificationStatus.IN_REVIEW
    assert result.risk_score == 0.60
    assert result.provider_name == "proveedor-kyc-c"


def test_traduce_clear_y_block_correctamente():
    fake_clear = FakeProviderCClient(
        {
            "referencia": "C-1",
            "decision": "CLEAR",
            "bandaRiesgo": "LOW",
        }
    )

    fake_block = FakeProviderCClient(
        {
            "referencia": "C-2",
            "decision": "BLOCK",
            "bandaRiesgo": "HIGH",
        }
    )

    approved = KYCProviderCAdapter(client=fake_clear).verify(_request())
    rejected = KYCProviderCAdapter(client=fake_block).verify(_request())

    assert approved.status == VerificationStatus.APPROVED
    assert approved.risk_score == 0.20

    assert rejected.status == VerificationStatus.REJECTED
    assert rejected.risk_score == 0.90