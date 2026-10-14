from fastapi.testclient import TestClient

from app.api.oauth_socios import obtener_servicio_autenticacion_socios
from app.main import app
from app.socios.dominio.credenciales import TokenAccesoSocio
from app.socios.servicio_autenticacion import CredencialesIntegracionInvalidas


class ServicioAutenticacionFalso:
    def __init__(self, valido: bool = True) -> None:
        self.valido = valido

    def autenticar(self, client_id: str, client_secret: str) -> TokenAccesoSocio:
        if not self.valido:
            raise CredencialesIntegracionInvalidas(client_id)
        assert client_id == "solv_cliente_001"
        assert client_secret == "solv_secret_correcto"
        return TokenAccesoSocio(
            access_token="jwt-socio",
            expires_in=900,
            scope="cotizaciones:crear",
        )


def test_endpoint_intercambia_client_credentials_por_token() -> None:
    app.dependency_overrides[obtener_servicio_autenticacion_socios] = (
        lambda: ServicioAutenticacionFalso()
    )
    try:
        with TestClient(app) as cliente:
            respuesta = cliente.post(
                "/api/v1/oauth/token",
                data={"grant_type": "client_credentials"},
                auth=("solv_cliente_001", "solv_secret_correcto"),
            )
    finally:
        app.dependency_overrides.clear()

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "access_token": "jwt-socio",
        "token_type": "bearer",
        "expires_in": 900,
        "scope": "cotizaciones:crear",
    }


def test_endpoint_rechaza_credenciales_invalidas() -> None:
    app.dependency_overrides[obtener_servicio_autenticacion_socios] = (
        lambda: ServicioAutenticacionFalso(valido=False)
    )
    try:
        with TestClient(app) as cliente:
            respuesta = cliente.post(
                "/api/v1/oauth/token",
                data={"grant_type": "client_credentials"},
                auth=("solv_cliente_001", "secreto-incorrecto"),
            )
    finally:
        app.dependency_overrides.clear()

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Las credenciales del socio no son válidas."


def test_endpoint_rechaza_un_grant_type_distinto() -> None:
    app.dependency_overrides[obtener_servicio_autenticacion_socios] = (
        lambda: ServicioAutenticacionFalso()
    )
    try:
        with TestClient(app) as cliente:
            respuesta = cliente.post(
                "/api/v1/oauth/token",
                data={"grant_type": "password"},
                auth=("solv_cliente_001", "solv_secret_correcto"),
            )
    finally:
        app.dependency_overrides.clear()

    assert respuesta.status_code == 400
