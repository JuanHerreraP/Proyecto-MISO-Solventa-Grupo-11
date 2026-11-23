"""Correo de bienvenida y notificación de confirmación de la póliza (HU12), y correos de la
renovación automática (HU17).

Por ahora solo hay adaptador simulado: registra el envío en el log y lo guarda en memoria para
las pruebas. Escribe con nivel WARNING, como el simulador de la firma, para que se vea en la
consola con la configuración por defecto de uvicorn (que oculta los mensajes INFO).

Pasar a SES o a SMTP es escribir otro adaptador de `EnviadorCorreo`.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
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
        logger.warning(
            "[CORREO SIMULADO] Bienvenida a %s: póliza %s, adjunto %s (%d bytes)",
            correo.destinatario,
            correo.numero_poliza,
            correo.nombre_adjunto,
            len(correo.adjunto_pdf),
        )
        self.correos.append(correo)

    def confirmar_emision(self, notificacion: NotificacionEmision) -> None:
        logger.warning(
            "[NOTIFICACION SIMULADA] Cliente %s: póliza %s emitida",
            notificacion.cliente_id,
            notificacion.numero_poliza,
        )
        self.notificaciones.append(notificacion)


# --- Renovación automática (HU17) -------------------------------------------------------


@dataclass(frozen=True)
class CorreoPreavisoRenovacion:
    """Aviso 30 días antes del vencimiento con la prima de la renovación ya recalculada."""

    destinatario: str
    nombre: str
    numero_poliza: str
    nombre_ramo: str
    vence_el: date
    nuevo_inicio: date
    nuevo_fin: date
    prima_actual: Decimal
    prima_renovacion: Decimal
    moneda: str
    renovacion_automatica_activa: bool
    tarjeta_ultimos_digitos: str | None


@dataclass(frozen=True)
class CorreoRenovacionEmitida:
    """La póliza se renovó: lleva adjunto el documento contractual del nuevo periodo."""

    destinatario: str
    nombre: str
    numero_poliza: str
    nuevo_inicio: date
    nuevo_fin: date
    prima_total: Decimal
    moneda: str
    nombre_adjunto: str
    adjunto_pdf: bytes


@dataclass(frozen=True)
class CorreoRenovacionNoRealizada:
    """No se pudo cobrar la renovación automática; el cliente aún puede pagarla a mano."""

    destinatario: str
    nombre: str
    numero_poliza: str
    vence_el: date
    motivo: str
    pagar_hasta: datetime | None


class EnviadorCorreoRenovacion(Protocol):
    def enviar_preaviso_renovacion(self, correo: CorreoPreavisoRenovacion) -> None: ...

    def enviar_renovacion_emitida(self, correo: CorreoRenovacionEmitida) -> None: ...

    def enviar_renovacion_no_realizada(self, correo: CorreoRenovacionNoRealizada) -> None: ...


class CorreoRenovacionSimulado:
    """Cumple `EnviadorCorreoRenovacion` sin salir del proceso."""

    def __init__(self):
        self.preavisos: list[CorreoPreavisoRenovacion] = []
        self.renovaciones: list[CorreoRenovacionEmitida] = []
        self.no_realizadas: list[CorreoRenovacionNoRealizada] = []

    def enviar_preaviso_renovacion(self, correo: CorreoPreavisoRenovacion) -> None:
        logger.warning(
            "[CORREO SIMULADO] Preaviso de renovación a %s: póliza %s vence el %s, "
            "nueva prima %s %s, renovación automática %s",
            correo.destinatario,
            correo.numero_poliza,
            correo.vence_el.isoformat(),
            correo.prima_renovacion,
            correo.moneda,
            "activa" if correo.renovacion_automatica_activa else "desactivada",
        )
        self.preavisos.append(correo)

    def enviar_renovacion_emitida(self, correo: CorreoRenovacionEmitida) -> None:
        logger.warning(
            "[CORREO SIMULADO] Póliza %s renovada para %s: vigencia %s a %s, adjunto %s (%d bytes)",
            correo.numero_poliza,
            correo.destinatario,
            correo.nuevo_inicio.isoformat(),
            correo.nuevo_fin.isoformat(),
            correo.nombre_adjunto,
            len(correo.adjunto_pdf),
        )
        self.renovaciones.append(correo)

    def enviar_renovacion_no_realizada(self, correo: CorreoRenovacionNoRealizada) -> None:
        logger.warning(
            "[CORREO SIMULADO] Renovación automática de la póliza %s no realizada para %s: %s",
            correo.numero_poliza,
            correo.destinatario,
            correo.motivo,
        )
        self.no_realizadas.append(correo)
