"""Publicación de eventos de negocio en Amazon SNS.

El tópico reparte cada evento a las colas SQS suscritas (hoy, la de pagos automáticos). Quien
publica no conoce a los consumidores: Siniestros solo avisa que aprobó un siniestro paramétrico.

Sin `SNS_TOPIC_ARN` no hay publicador y el sistema conserva su comportamiento síncrono (ordenar
el desembolso en el mismo proceso), que es el de desarrollo local y el de las pruebas.
"""

import logging
import os
from functools import lru_cache
from typing import Protocol

from app.eventos.modelos import EventoNegocio

logger = logging.getLogger(__name__)


class PublicacionFallida(Exception):
    """El transporte no confirmó la recepción del evento."""


class PublicadorNegocio(Protocol):
    """Publica un evento y devuelve el identificador que asigna el transporte."""

    def publicar(self, evento: EventoNegocio) -> str: ...


class PublicadorSNS:
    """Publica en un tópico de SNS. Lee el ARN de `SNS_TOPIC_ARN`.

    El cliente se crea de forma perezosa para no requerir credenciales al importar el módulo.
    """

    def __init__(self, topic_arn: str | None = None, cliente=None):
        self._topic_arn = topic_arn or os.getenv("SNS_TOPIC_ARN")
        if not self._topic_arn:
            raise ValueError("SNS_TOPIC_ARN no está definido: no se puede publicar en SNS.")
        self._cliente = cliente

    def _sns(self):
        if self._cliente is None:
            import boto3

            self._cliente = boto3.client("sns", region_name=os.getenv("AWS_DEFAULT_REGION"))
        return self._cliente

    def publicar(self, evento: EventoNegocio) -> str:
        try:
            respuesta = self._sns().publish(
                TopicArn=self._topic_arn,
                Message=evento.como_json(),
                MessageAttributes={
                    "tipo": {"DataType": "String", "StringValue": evento.tipo.value}
                },
            )
        except Exception as error:  # noqa: BLE001 — cualquier fallo de red o de boto3 se traduce.
            logger.warning("SNS rechazó el evento %s: %s", evento.evento_id, error)
            raise PublicacionFallida(str(error)) from error
        message_id = respuesta.get("MessageId")
        if not message_id:
            raise PublicacionFallida("SNS no devolvió MessageId: evento no confirmado.")
        return message_id


class PublicadorEnMemoria:
    """Publicador para pruebas y desarrollo: guarda los eventos en `eventos`."""

    def __init__(self):
        self.eventos: list[EventoNegocio] = []

    def publicar(self, evento: EventoNegocio) -> str:
        self.eventos.append(evento)
        return f"mem-{len(self.eventos)}"


@lru_cache(maxsize=1)
def publicador_negocio() -> PublicadorNegocio | None:
    """El publicador del proceso, o None si no hay tópico configurado.

    Uno por proceso: crear un cliente de AWS en cada solicitud sería lento.
    """
    if os.getenv("SNS_TOPIC_ARN"):
        return PublicadorSNS()
    return None
