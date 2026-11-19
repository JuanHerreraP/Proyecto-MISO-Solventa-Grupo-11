"""Canal de envío del push (HU05): puerto, adaptador simulado y selección por configuración.

El servicio de notificaciones decide **qué** push mandar (`PushPendiente`); el canal lo **envía**.
Hay dos adaptadores: el simulado, que solo escribe en el log (desarrollo y pruebas), y el de FCM
(`app/notificaciones/fcm.py`), que llega al teléfono de verdad. Se elige con `PUSH_PROVEEDOR`.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Protocol

from app.notificaciones.modelos import PushPendiente

logger = logging.getLogger(__name__)


class ConfiguracionPushInvalida(Exception):
    """El canal de push está mal configurado (proveedor desconocido o credenciales inválidas)."""


@dataclass(frozen=True)
class ResultadoEnvio:
    """Qué pasó con cada token del push."""

    enviados: tuple[str, ...] = ()
    # El proveedor dice que el token ya no sirve (app desinstalada, token vencido): hay que
    # darlo de baja para no volver a intentarlo.
    tokens_invalidos: tuple[str, ...] = ()
    # Falló por algo pasajero (red, cuota, servicio caído): el token sigue siendo válido.
    fallidos: tuple[str, ...] = ()


class EnviadorPush(Protocol):
    def enviar(self, push: PushPendiente) -> ResultadoEnvio:
        """Envía el push a todos sus tokens. Un token que falla se informa, no lanza."""
        ...


def enmascarar(token: str) -> str:
    """Los tokens son credenciales del dispositivo: en el log solo se muestra el final."""
    return f"…{token[-6:]}" if len(token) > 6 else "…"


@dataclass
class EnviadorPushSimulado:
    """Cumple `EnviadorPush` sin salir del proceso.

    Comportamiento según el token, como la pasarela de pagos simulada:
    - `tok_invalido*` -> token inválido (se da de baja)
    - `tok_caido*`    -> falla pasajera
    - cualquier otro  -> enviado
    """

    enviados: list[PushPendiente] = field(default_factory=list)

    def enviar(self, push: PushPendiente) -> ResultadoEnvio:
        ok, invalidos, fallidos = [], [], []
        for token in push.tokens:
            if token.startswith("tok_invalido"):
                invalidos.append(token)
            elif token.startswith("tok_caido"):
                fallidos.append(token)
            else:
                ok.append(token)
        if ok:
            self.enviados.append(push)
            # Nivel WARNING, como los demás simuladores, para que se vea con uvicorn por defecto.
            logger.warning(
                "[PUSH SIMULADO] a %s (%d dispositivo(s): %s): %s — %s%s",
                push.cliente_id,
                len(ok),
                ", ".join(enmascarar(t) for t in ok),
                push.titulo,
                push.cuerpo,
                " [agrupado]" if push.agrupado else "",
            )
        return ResultadoEnvio(tuple(ok), tuple(invalidos), tuple(fallidos))


def crear_enviador_push() -> EnviadorPush:
    """Elige el adaptador según la configuración.

    - `PUSH_PROVEEDOR=simulado` (por defecto): solo log.
    - `PUSH_PROVEEDOR=fcm`: Firebase Cloud Messaging. Las credenciales de la cuenta de servicio
      salen de `FCM_CREDENCIALES_JSON` (el contenido, pensado para un secreto de AWS) o de
      `FCM_CREDENCIALES_PATH` (la ruta del archivo, para desarrollo local).
    """
    proveedor = (os.getenv("PUSH_PROVEEDOR") or "simulado").strip().lower()
    if proveedor == "simulado":
        return EnviadorPushSimulado()
    if proveedor == "fcm":
        from app.notificaciones.fcm import EnviadorPushFCM, cargar_credenciales

        credenciales = cargar_credenciales(
            ruta=os.getenv("FCM_CREDENCIALES_PATH") or None,
            contenido=os.getenv("FCM_CREDENCIALES_JSON") or None,
        )
        return EnviadorPushFCM(credenciales)
    raise ConfiguracionPushInvalida(
        f"PUSH_PROVEEDOR desconocido: {proveedor!r}. Usa 'simulado' o 'fcm'."
    )
