"""Cliente HTTP hacia Solventa para el proveedor externo simulado (HU20).

Aísla la comunicación de red del resto del servicio: la API del proveedor y la generación de
eventos no deben saber cómo se habla con Solventa. La URL y la credencial se leen de variables
de entorno; nunca se escriben en el código.

Preparado para sustituir la API Key por OAuth Client Credentials, API Gateway u otro mecanismo
más robusto: bastaría cambiar cómo se arma la cabecera de autenticación aquí.
"""

import os

import httpx

URL_POR_DEFECTO = "http://localhost:8000/api/v1/integraciones/telemetria/eventos"
API_KEY_POR_DEFECTO = "solventa-telemetry-dev"
TIMEOUT_POR_DEFECTO = 5.0


class ErrorEntregaSolventa(Exception):
    """Solventa no está disponible (no responde, rechaza la conexión o hace timeout)."""


class ErrorRespuestaSolventa(Exception):
    """Solventa respondió con un código de error (401, 403, 422, 500, ...)."""

    def __init__(self, status_code: int, cuerpo: object):
        super().__init__(f"Solventa respondió {status_code}")
        self.status_code = status_code
        self.cuerpo = cuerpo


class ClienteSolventa:
    """Envía eventos de telemetría a Solventa mediante HTTP POST + X-API-Key."""

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        timeout: float = TIMEOUT_POR_DEFECTO,
    ):
        self._url = url or os.getenv("SOLVENTA_TELEMETRY_URL", URL_POR_DEFECTO)
        self._api_key = api_key or os.getenv("SOLVENTA_TELEMETRY_API_KEY", API_KEY_POR_DEFECTO)
        self._timeout = timeout

    @property
    def url(self) -> str:
        return self._url

    def _cabeceras(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-API-Key": self._api_key,
        }

    def enviar_evento(self, evento: dict) -> int:
        """Empuja el evento hacia Solventa y devuelve el código HTTP de éxito.

        Lanza `ErrorEntregaSolventa` si Solventa no responde o hay timeout, y
        `ErrorRespuestaSolventa` si responde con un código >= 400. Los errores no se ocultan.
        """
        try:
            with httpx.Client(timeout=self._timeout) as cliente:
                respuesta = cliente.post(self._url, json=evento, headers=self._cabeceras())
        except httpx.TimeoutException as error:
            raise ErrorEntregaSolventa("Timeout al contactar a Solventa.") from error
        except httpx.HTTPError as error:
            raise ErrorEntregaSolventa("No fue posible contactar a Solventa.") from error

        if respuesta.status_code >= 400:
            try:
                cuerpo = respuesta.json()
            except ValueError:
                cuerpo = respuesta.text
            raise ErrorRespuestaSolventa(respuesta.status_code, cuerpo)

        return respuesta.status_code
