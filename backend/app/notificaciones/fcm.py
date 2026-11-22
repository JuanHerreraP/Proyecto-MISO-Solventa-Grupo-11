"""Adaptador de Firebase Cloud Messaging (API HTTP v1) para el push (HU05).

Autenticación: la cuenta de servicio de Firebase firma un JWT (RS256) que se cambia en Google por
un token de acceso de una hora; se reutiliza mientras no venza. Envío: una petición por token
(la API v1 no tiene envío múltiple). Solo usa `httpx` y `PyJWT`, que ya son dependencias.

La credencial es un secreto: nunca se escribe en el log ni en los mensajes de error.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import jwt

from app.notificaciones.canal import ConfiguracionPushInvalida, ResultadoEnvio, enmascarar
from app.notificaciones.modelos import PushPendiente

logger = logging.getLogger(__name__)

URL_TOKEN_POR_DEFECTO = "https://oauth2.googleapis.com/token"
ALCANCE = "https://www.googleapis.com/auth/firebase.messaging"
URL_ENVIO = "https://fcm.googleapis.com/v1/projects/{proyecto}/messages:send"
# Debe coincidir con el canal que crea la app Android.
CANAL_ANDROID = "solventa_notificaciones"

# Errores de FCM que significan que el token ya no sirve y hay que darlo de baja.
_CODIGOS_TOKEN_INVALIDO = {"UNREGISTERED", "SENDER_ID_MISMATCH"}
_CAMPOS_CREDENCIALES = ("project_id", "client_email", "private_key")
# Margen para renovar el token de acceso antes de que venza.
_MARGEN_VENCIMIENTO = timedelta(minutes=5)


@dataclass(frozen=True)
class CredencialesFCM:
    project_id: str
    client_email: str
    private_key: str = ""
    token_uri: str = URL_TOKEN_POR_DEFECTO

    def __repr__(self) -> str:  # nunca muestra la llave privada
        return (
            f"CredencialesFCM(project_id={self.project_id!r}, client_email={self.client_email!r})"
        )


def cargar_credenciales(ruta: str | None = None, contenido: str | None = None) -> CredencialesFCM:
    """Lee la cuenta de servicio de Firebase, del contenido JSON o de un archivo."""
    if contenido is None and ruta is None:
        raise ConfiguracionPushInvalida(
            "Falta la credencial de FCM: define FCM_CREDENCIALES_JSON o FCM_CREDENCIALES_PATH."
        )
    if contenido is None:
        try:
            contenido = Path(ruta).read_text(encoding="utf-8")
        except OSError:
            raise ConfiguracionPushInvalida(
                "No se pudo leer el archivo de credenciales de FCM (FCM_CREDENCIALES_PATH)."
            ) from None
    try:
        datos = json.loads(contenido)
    except json.JSONDecodeError:
        raise ConfiguracionPushInvalida("La credencial de FCM no es un JSON válido.") from None
    if not isinstance(datos, dict):
        raise ConfiguracionPushInvalida("La credencial de FCM no tiene el formato esperado.")
    faltantes = [c for c in _CAMPOS_CREDENCIALES if not datos.get(c)]
    if faltantes:
        raise ConfiguracionPushInvalida(
            f"La credencial de FCM no trae los campos: {', '.join(faltantes)}."
        )
    return CredencialesFCM(
        project_id=datos["project_id"],
        client_email=datos["client_email"],
        private_key=datos["private_key"],
        token_uri=datos.get("token_uri") or URL_TOKEN_POR_DEFECTO,
    )


class _AccesoNoDisponible(Exception):
    """No se pudo obtener el token de acceso de Google."""


class EnviadorPushFCM:
    def __init__(
        self,
        credenciales: CredencialesFCM,
        cliente: httpx.Client | None = None,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        timeout: float = 10.0,
    ):
        self._credenciales = credenciales
        self._cliente = cliente or httpx.Client(timeout=timeout)
        self._reloj = reloj
        self._token_acceso: str | None = None
        self._vence_en: datetime | None = None

    # --- Envío ------------------------------------------------------------------------------

    def enviar(self, push: PushPendiente) -> ResultadoEnvio:
        enviados, invalidos, fallidos = [], [], []
        for token in push.tokens:
            resultado = self._enviar_a(push, token)
            {"enviado": enviados, "invalido": invalidos, "fallido": fallidos}[resultado].append(
                token
            )
        return ResultadoEnvio(tuple(enviados), tuple(invalidos), tuple(fallidos))

    def _enviar_a(self, push: PushPendiente, token: str) -> str:
        try:
            respuesta = self._post(push, token)
            if respuesta.status_code == 401:
                # El token de acceso pudo vencer o revocarse: se pide otro y se reintenta una vez.
                self._olvidar_acceso()
                respuesta = self._post(push, token)
        except _AccesoNoDisponible:
            return "fallido"
        except httpx.HTTPError as error:
            logger.warning("FCM no respondió para %s: %s", enmascarar(token), type(error).__name__)
            return "fallido"

        if respuesta.is_success:
            return "enviado"
        codigo = _codigo_de_error(respuesta)
        if codigo in _CODIGOS_TOKEN_INVALIDO or _token_malformado(respuesta, codigo):
            return "invalido"
        logger.warning(
            "FCM rechazó el envío a %s: HTTP %s %s",
            enmascarar(token),
            respuesta.status_code,
            codigo or "",
        )
        return "fallido"

    def _post(self, push: PushPendiente, token: str) -> httpx.Response:
        return self._cliente.post(
            URL_ENVIO.format(proyecto=self._credenciales.project_id),
            json=self._mensaje(push, token),
            headers={"Authorization": f"Bearer {self._acceso()}"},
        )

    @staticmethod
    def _mensaje(push: PushPendiente, token: str) -> dict[str, object]:
        return {
            "message": {
                "token": token,
                "notification": {"title": push.titulo, "body": push.cuerpo},
                # FCM exige que todos los valores de `data` sean texto.
                "data": {clave: str(valor) for clave, valor in push.datos.items()},
                "android": {
                    "priority": "HIGH",
                    "notification": {
                        "channel_id": CANAL_ANDROID,
                        # Misma etiqueta: este aviso reemplaza al anterior del grupo.
                        "tag": push.etiqueta,
                        # En la pantalla bloqueada no se ve el contenido (trae montos).
                        "visibility": "PRIVATE",
                    },
                },
            }
        }

    # --- Token de acceso --------------------------------------------------------------------

    def _acceso(self) -> str:
        ahora = self._reloj()
        if self._token_acceso and self._vence_en and ahora < self._vence_en - _MARGEN_VENCIMIENTO:
            return self._token_acceso
        return self._pedir_acceso(ahora)

    def _olvidar_acceso(self) -> None:
        self._token_acceso = None
        self._vence_en = None

    def _pedir_acceso(self, ahora: datetime) -> str:
        c = self._credenciales
        asercion = jwt.encode(
            {
                "iss": c.client_email,
                "scope": ALCANCE,
                "aud": c.token_uri,
                "iat": int(ahora.timestamp()),
                "exp": int((ahora + timedelta(hours=1)).timestamp()),
            },
            c.private_key,
            algorithm="RS256",
        )
        try:
            respuesta = self._cliente.post(
                c.token_uri,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": asercion,
                },
            )
            respuesta.raise_for_status()
            cuerpo = respuesta.json()
            acceso = cuerpo["access_token"]
            duracion = int(cuerpo.get("expires_in", 3600))
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            # Sin detalle del error: la respuesta de Google podría repetir la credencial.
            logger.error("No se pudo obtener el token de acceso de FCM (%s)", type(error).__name__)
            raise _AccesoNoDisponible() from None
        self._token_acceso = acceso
        self._vence_en = ahora + timedelta(seconds=duracion)
        return acceso


def _codigo_de_error(respuesta: httpx.Response) -> str | None:
    """El `errorCode` de FCM si lo trae; si no, el `status` general (p. ej. INVALID_ARGUMENT)."""
    try:
        error = respuesta.json().get("error", {})
    except (ValueError, AttributeError):
        return None
    for detalle in error.get("details", []) or []:
        if isinstance(detalle, dict) and detalle.get("errorCode"):
            return detalle["errorCode"]
    return error.get("status")


def _token_malformado(respuesta: httpx.Response, codigo: str | None) -> bool:
    """INVALID_ARGUMENT también puede ser culpa del mensaje; solo cuenta si habla del token."""
    if codigo != "INVALID_ARGUMENT":
        return False
    try:
        mensaje = str(respuesta.json().get("error", {}).get("message", ""))
    except (ValueError, AttributeError):
        return False
    return "token" in mensaje.lower()
