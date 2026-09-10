"""
Suite de regresión del Experimento 3 (Puertos y Adaptadores / EC06).

Esta es la MISMA suite que se ejecuta contra el servicio de Identidad primero
con el Proveedor KYC A configurado y luego, sin cambiar ni una línea de estas
pruebas ni del servicio, con el Proveedor KYC B configurado (parametrización
`provider_name`). La matriz de GitHub Actions (`.github/workflows/
experimento-3-kyc-regression.yml`) ejecuta ambos casos por separado y publica
la evidencia de cada corrida.

Según la interpretación de resultados ya definida para este experimento:
- Si todas las pruebas pasan igual para "A" y para "B" -> hipótesis soportada
  (el cambio de proveedor queda aislado en el adaptador).
- Si alguna prueba requiere modificarse para uno de los proveedores, o si el
  comportamiento observado difiere entre proveedores para el mismo caso ->
  la hipótesis debe revisarse (ver README de este experimento).
"""
import pytest

PAYLOAD_BASE = {
    "customer_id": "cust-001",
    "consent_id": "consent-001",
    "document_type": "CC",
    "full_name": "Camila Rojas",
    "birth_date": "1990-05-12",
}

# Números de documento elegidos para caer, de forma determinística, en cada
# uno de los tres resultados posibles -- de manera equivalente en ambos
# proveedores simulados (ver `bucket` en kyc_provider_a.py / kyc_provider_b.py).
CASOS_POR_RESULTADO = [
    ("1000000001", "APPROVED"),
    ("1000000003", "IN_REVIEW"),
    ("1000000034", "REJECTED"),
]


@pytest.mark.parametrize("provider_name", ["A", "B"])
@pytest.mark.parametrize("document_number,expected_status", CASOS_POR_RESULTADO)
def test_verificacion_responde_200_y_el_estado_esperado(
    client_with_provider, provider_name, document_number, expected_status
):
    client = client_with_provider(provider_name)
    payload = {**PAYLOAD_BASE, "document_number": document_number}

    response = client.post("/identidad/verificaciones", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == expected_status


@pytest.mark.parametrize("provider_name", ["A", "B"])
def test_la_respuesta_cumple_el_contrato_esperado_por_el_consumidor(
    client_with_provider, provider_name
):
    client = client_with_provider(provider_name)
    payload = {**PAYLOAD_BASE, "document_number": "1000000001"}

    response = client.post("/identidad/verificaciones", json=payload)
    body = response.json()

    # El contrato hacia el consumidor no debe cambiar sin importar qué
    # proveedor esté configurado detrás del puerto.
    assert set(body.keys()) == {"verification_id", "status", "risk_score", "checked_at"}
    assert isinstance(body["verification_id"], str) and body["verification_id"]
    assert body["status"] in {"APPROVED", "REJECTED", "IN_REVIEW"}
    assert isinstance(body["risk_score"], float)
    assert 0.0 <= body["risk_score"] <= 1.0


@pytest.mark.parametrize("provider_name", ["A", "B"])
def test_la_validacion_de_entrada_es_igual_sin_importar_el_proveedor(
    client_with_provider, provider_name
):
    client = client_with_provider(provider_name)
    payload_incompleto = {"customer_id": "cust-001"}  # faltan campos requeridos

    response = client.post("/identidad/verificaciones", json=payload_incompleto)

    assert response.status_code == 422


@pytest.mark.parametrize("provider_name", ["A", "B"])
def test_salud_reporta_el_proveedor_activo_sin_exponer_su_contrato(
    client_with_provider, provider_name
):
    client = client_with_provider(provider_name)

    response = client.get("/salud")

    assert response.status_code == 200
    assert response.json()["proveedor_kyc_activo"] == provider_name
