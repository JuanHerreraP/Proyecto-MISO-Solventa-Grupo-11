"""Pruebas del cliente HTTP hacia Solventa (HU20).

Se mockea la llamada httpx para verificar URL, método, cuerpo y cabecera X-API-Key sin red,
y para comprobar el manejo de timeout y respuestas de error.
"""

import httpx
import pytest

from mocks.telemetry.cliente_solventa import (
    ClienteSolventa,
    ErrorEntregaSolventa,
    ErrorRespuestaSolventa,
)


class RespuestaFalsa:
    def __init__(self, status_code: int, json_data: object = None):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}

    def json(self):
        return self._json


class ClienteHttpxFalso:
    """Reemplaza httpx.Client: captura la llamada y devuelve una respuesta fija."""

    ultima_llamada: dict = {}

    def __init__(self, respuesta=None, excepcion=None, timeout=None):
        self._respuesta = respuesta
        self._excepcion = excepcion
        ClienteHttpxFalso.timeout_recibido = timeout

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, json, headers):
        ClienteHttpxFalso.ultima_llamada = {
            "url": url,
            "json": json,
            "headers": headers,
        }
        if self._excepcion is not None:
            raise self._excepcion
        return self._respuesta


EVENTO = {
    "evento_id": "FLIGHT-AV123-20261026-acde1234",
    "tipo_evento": "RETRASO_VUELO",
    "valor_observado": 215,
    "unidad": "MINUTOS",
    "fuente": "MOCK_FLIGHT_PROVIDER",
}


def test_envia_url_metodo_body_y_api_key(monkeypatch) -> None:
    def fabrica(timeout=None):
        return ClienteHttpxFalso(respuesta=RespuestaFalsa(200), timeout=timeout)

    monkeypatch.setattr(httpx, "Client", fabrica)

    cliente = ClienteSolventa(
        url="http://solventa.test/api/v1/integraciones/telemetria/eventos",
        api_key="clave-secreta",
        timeout=5.0,
    )
    status_code = cliente.enviar_evento(EVENTO)

    assert status_code == 200
    llamada = ClienteHttpxFalso.ultima_llamada
    assert llamada["url"] == "http://solventa.test/api/v1/integraciones/telemetria/eventos"
    assert llamada["json"] == EVENTO
    assert llamada["headers"]["X-API-Key"] == "clave-secreta"
    assert llamada["headers"]["Content-Type"] == "application/json"
    # Timeout configurado (no se deja la conexión esperando indefinidamente).
    assert ClienteHttpxFalso.timeout_recibido == 5.0


def test_lee_configuracion_de_variables_de_entorno(monkeypatch) -> None:
    monkeypatch.setenv("SOLVENTA_TELEMETRY_URL", "http://env.test/eventos")
    monkeypatch.setenv("SOLVENTA_TELEMETRY_API_KEY", "clave-env")

    def fabrica(timeout=None):
        return ClienteHttpxFalso(respuesta=RespuestaFalsa(200), timeout=timeout)

    monkeypatch.setattr(httpx, "Client", fabrica)

    cliente = ClienteSolventa()
    assert cliente.url == "http://env.test/eventos"
    cliente.enviar_evento(EVENTO)
    assert ClienteHttpxFalso.ultima_llamada["headers"]["X-API-Key"] == "clave-env"


def test_timeout_lanza_error_de_entrega(monkeypatch) -> None:
    def fabrica(timeout=None):
        return ClienteHttpxFalso(excepcion=httpx.TimeoutException("lento"), timeout=timeout)

    monkeypatch.setattr(httpx, "Client", fabrica)

    cliente = ClienteSolventa(url="http://x/eventos", api_key="k")
    with pytest.raises(ErrorEntregaSolventa):
        cliente.enviar_evento(EVENTO)


def test_conexion_rechazada_lanza_error_de_entrega(monkeypatch) -> None:
    def fabrica(timeout=None):
        return ClienteHttpxFalso(excepcion=httpx.ConnectError("sin conexión"), timeout=timeout)

    monkeypatch.setattr(httpx, "Client", fabrica)

    cliente = ClienteSolventa(url="http://x/eventos", api_key="k")
    with pytest.raises(ErrorEntregaSolventa):
        cliente.enviar_evento(EVENTO)


@pytest.mark.parametrize("codigo", [401, 403, 422, 500])
def test_respuesta_de_error_lanza_error_de_respuesta(monkeypatch, codigo) -> None:
    def fabrica(timeout=None):
        return ClienteHttpxFalso(
            respuesta=RespuestaFalsa(codigo, {"detail": "nope"}), timeout=timeout
        )

    monkeypatch.setattr(httpx, "Client", fabrica)

    cliente = ClienteSolventa(url="http://x/eventos", api_key="k")
    with pytest.raises(ErrorRespuestaSolventa) as exc:
        cliente.enviar_evento(EVENTO)
    assert exc.value.status_code == codigo
