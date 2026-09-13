import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client_with_provider(monkeypatch):
    """
    Construye un TestClient del servicio de Identidad con el proveedor KYC
    indicado ya configurado (variable de entorno KYC_PROVIDER), sin tocar
    ninguna línea del servicio: la selección de adaptador ocurre en
    `get_identity_verification_provider`, que lee la variable en cada
    solicitud.
    """

    def _build(provider_name: str) -> TestClient:
        monkeypatch.setenv("KYC_PROVIDER", provider_name)
        return TestClient(app)

    return _build
