"""Pruebas de escenarios inválidos del adaptador KYC Provider A."""

from datetime import date

import pytest

from app.identidad.adaptadores.kyc_provider_a import (
    KYCProviderAAdapter,
    ProviderAClient,
)
from app.identidad.modelos import (
    VerificationRequest,
)


class FakeProviderAClient(ProviderAClient):
    def __init__(self, response: dict):
        self._response = response

    def verificar_identidad(
        self,
        document_type,
        document_number,
        full_name,
        birth_date,
    ):
        return self._response


def _request() -> VerificationRequest:
    return VerificationRequest(
        customer_id="c1",
        consent_id="consent-1",
        document_type="CC",
        document_number="123456789",
        full_name="Ana Perez",
        birth_date=date(
            1995,
            1,
            1,
        ),
    )


def test_score_cero_se_normaliza_a_cero():
    fake = FakeProviderAClient(
        {
            "verificationId": "A-0",
            "status": "APPROVED",
            "score": 0,
        }
    )

    adapter = KYCProviderAAdapter(client=fake)

    resultado = adapter.verify(_request())

    assert resultado.risk_score == 0.0


def test_score_cien_se_normaliza_a_uno():
    fake = FakeProviderAClient(
        {
            "verificationId": "A-100",
            "status": "REJECTED",
            "score": 100,
        }
    )

    adapter = KYCProviderAAdapter(client=fake)

    resultado = adapter.verify(_request())

    assert resultado.risk_score == 1.0


def test_estado_externo_desconocido_no_es_aceptado():
    fake = FakeProviderAClient(
        {
            "verificationId": "A-X",
            "status": "UNKNOWN",
            "score": 50,
        }
    )

    adapter = KYCProviderAAdapter(client=fake)

    with pytest.raises(KeyError):
        adapter.verify(_request())


def test_respuesta_sin_verification_id_no_es_aceptada():
    fake = FakeProviderAClient(
        {
            "status": "APPROVED",
            "score": 20,
        }
    )

    adapter = KYCProviderAAdapter(client=fake)

    with pytest.raises(KeyError):
        adapter.verify(_request())


def test_respuesta_sin_score_no_es_aceptada():
    fake = FakeProviderAClient(
        {
            "verificationId": "A-1",
            "status": "APPROVED",
        }
    )

    adapter = KYCProviderAAdapter(client=fake)

    with pytest.raises(KeyError):
        adapter.verify(_request())
