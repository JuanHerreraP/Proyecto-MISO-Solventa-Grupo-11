"""Correo de bienvenida y notificación de confirmación de la póliza (HU12).

Por ahora solo hay adaptador simulado: registra el envío en el log y lo guarda en memoria para
las pruebas. Pasar a SES o a SMTP es escribir otro adaptador de `EnviadorCorreo`.
"""

import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


class ComunicacionNoDisponible(Exception):
    """El canal no pudo entregar el mensaje."""


@dataclass(frozen=True)
class CorreoBienvenida:
    destinatario: str
    nombre: str
    numero_poliza: str
    nombre_adjunto: str
    adjunto_pdf: bytes


@dataclass(frozen=True)
class NotificacionEmision:
    cliente_id: str
    poliza_id: str
    numero_poliza: str


class EnviadorCorreo(Protocol):
    def enviar_bienvenida(self, correo: CorreoBienvenida) -> None: ...


class Notificador(Protocol):
    def confirmar_emision(self, notificacion: NotificacionEmision) -> None: ...


class ComunicacionesSimuladas:
    """Cumple `EnviadorCorreo` y `Notificador` sin salir del proceso."""

    def __init__(self):
        self.correos: list[CorreoBienvenida] = []
        self.notificaciones: list[NotificacionEmision] = []

    def enviar_bienvenida(self, correo: CorreoBienvenida) -> None:
        # El log no incluye el contenido del adjunto ni el nombre completo del cliente.
        logger.info(
            "Correo simulado a %s: póliza %s, adjunto %s (%d bytes)",
            correo.destinatario,
            correo.numero_poliza,
            correo.nombre_adjunto,
            len(correo.adjunto_pdf),
        )
        self.correos.append(correo)

    def confirmar_emision(self, notificacion: NotificacionEmision) -> None:
        logger.info(
            "Notificación simulada al cliente %s: póliza %s emitida",
            notificacion.cliente_id,
            notificacion.numero_poliza,
        )
        self.notificaciones.append(notificacion)
