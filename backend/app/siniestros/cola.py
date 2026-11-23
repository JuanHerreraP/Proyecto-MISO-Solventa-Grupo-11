"""Publicación de eventos de telemetría hacia una cola (HU20, EC — contrapresión).

La ingesta deja de procesar el evento en línea: lo pone en una cola y responde 202. Un worker
aparte lo consume a su ritmo, lo que absorbe los picos del proveedor externo sin tumbar el
backend. Esta abstracción desacopla el endpoint del transporte: en AWS es Amazon SQS, en pruebas
es una cola en memoria.

El publicador falla con `PublicacionFallida` cuando el transporte no confirma la recepción
(SQS no devuelve `MessageId`): así la API puede responder 503 y el proveedor reintenta, en vez
de dar por recibido un evento que se perdió.
"""

import json
import logging
import os
from typing import Protocol

logger = logging.getLogger(__name__)


class PublicacionFallida(Exception):
    """El transporte no confirmó la recepción del evento."""


class PublicadorEventos(Protocol):
    """Pone un evento en la cola y devuelve el identificador que asigna el transporte."""

    def publicar(self, evento: dict) -> str: ...


class PublicadorSQS:
    """Publica en Amazon SQS. Lee la URL de la cola de `SQS_QUEUE_URL`.

    La región sale de `AWS_DEFAULT_REGION` (boto3 ya la resuelve del entorno estándar de AWS).
    El cliente se crea de forma perezosa para no requerir credenciales al importar el módulo.
    """

    def __init__(self, url_cola: str | None = None, cliente=None):
        self._url_cola = url_cola or os.getenv("SQS_QUEUE_URL")
        if not self._url_cola:
            raise ValueError("SQS_QUEUE_URL no está definido: no se puede publicar en SQS.")
        self._cliente = cliente

    def _sqs(self):
        if self._cliente is None:
            import boto3

            self._cliente = boto3.client("sqs", region_name=os.getenv("AWS_DEFAULT_REGION"))
        return self._cliente

    def publicar(self, evento: dict) -> str:
        try:
            respuesta = self._sqs().send_message(
                QueueUrl=self._url_cola,
                MessageBody=json.dumps(evento, default=str),
            )
        except Exception as error:  # noqa: BLE001 — cualquier fallo de red/boto3 se traduce.
            logger.warning("SQS rechazó el evento %s: %s", evento.get("evento_id"), error)
            raise PublicacionFallida(str(error)) from error
        message_id = respuesta.get("MessageId")
        if not message_id:
            raise PublicacionFallida("SQS no devolvió MessageId: evento no confirmado.")
        return message_id


class PublicadorEnMemoria:
    """Cola en memoria para pruebas y desarrollo local sin SQS.

    Guarda los eventos publicados en `mensajes` y asigna un `MessageId` incremental.
    """

    def __init__(self):
        self.mensajes: list[dict] = []

    def publicar(self, evento: dict) -> str:
        self.mensajes.append(evento)
        return f"mem-{len(self.mensajes)}"


def construir_publicador() -> PublicadorEventos:
    """Elige el publicador por entorno: SQS si hay `SQS_QUEUE_URL`, si no en memoria."""
    if os.getenv("SQS_QUEUE_URL"):
        return PublicadorSQS()
    return PublicadorEnMemoria()
