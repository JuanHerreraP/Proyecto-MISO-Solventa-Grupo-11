"""Pruebas del cliente HTTP del Proveedor KYC A.

Estas pruebas validan la comunicación HTTP que realiza el cliente externo
sin involucrar la lógica de traducción del adaptador.
"""

import httpx
import pytest

from app.identidad.adaptadores.kyc_provider_a import ProviderAClient


def test_provider_a_envia_el_contrato_http_correcto(monkeypatch):
    llamada = {}

    def fake_post(
        url,
        json,
        timeout,
    ):
        llamada["url"] = url
        llamada["json"] = json
        llamada["timeout"] = timeout

        request = httpx.Request(
            "POST",
            url,
        )

        return httpx.Response(
            status_code=200,
            request=request,
            json={
                "verificationId": "A-123",
                "status": "APPROVED",
                "score": 25,
            },
        )

    monkeypatch.setattr(
        httpx,
        "post",
        fake_post,
    )

    client = ProviderAClient(
        base_url="http://provider-a.test",
        timeout=2.5,
    )

    resultado = client.verificar_identidad(
        document_type="CC",
        document_number="123456789",
        full_name="Ana Perez",
        birth_date="1995-01-01",
    )

    assert llamada["url"] == (
        "http://provider-a.test/kyc/verify"
    )

    assert llamada["json"] == {
        "documentType": "CC",
        "documentNumber": "123456789",
        "fullName": "Ana Perez",
        "birthDate": "1995-01-01",
    }

    assert llamada["timeout"] == 2.5

    assert resultado == {
        "verificationId": "A-123",
        "status": "APPROVED",
        "score": 25,
    }


def test_provider_a_propaga_error_de_conexion(monkeypatch):
    def fake_post(
        url,
        json,
        timeout,
    ):
        request = httpx.Request(
            "POST",
            url,
        )

        raise httpx.ConnectError(
            "Proveedor no disponible",
            request=request,
        )

    monkeypatch.setattr(
        httpx,
        "post",
        fake_post,
    )

    client = ProviderAClient(
        base_url="http://provider-a.test",
    )

    with pytest.raises(httpx.ConnectError):
        client.verificar_identidad(
            document_type="CC",
            document_number="123456789",
            full_name="Ana Perez",
            birth_date="1995-01-01",
        )


def test_provider_a_propaga_timeout(monkeypatch):
    def fake_post(
        url,
        json,
        timeout,
    ):
        request = httpx.Request(
            "POST",
            url,
        )

        raise httpx.ReadTimeout(
            "El proveedor excedió el tiempo de espera",
            request=request,
        )

    monkeypatch.setattr(
        httpx,
        "post",
        fake_post,
    )

    client = ProviderAClient(
        base_url="http://provider-a.test",
        timeout=0.1,
    )

    with pytest.raises(httpx.ReadTimeout):
        client.verificar_identidad(
            document_type="CC",
            document_number="123456789",
            full_name="Ana Perez",
            birth_date="1995-01-01",
        )


def test_provider_a_propaga_error_http_500(monkeypatch):
    def fake_post(
        url,
        json,
        timeout,
    ):
        request = httpx.Request(
            "POST",
            url,
        )

        return httpx.Response(
            status_code=500,
            request=request,
            json={
                "detail": "Error interno del proveedor"
            },
        )

    monkeypatch.setattr(
        httpx,
        "post",
        fake_post,
    )

    client = ProviderAClient(
        base_url="http://provider-a.test",
    )

    with pytest.raises(httpx.HTTPStatusError):
        client.verificar_identidad(
            document_type="CC",
            document_number="123456789",
            full_name="Ana Perez",
            birth_date="1995-01-01",
        )