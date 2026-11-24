"""Eventos de negocio que viajan por SNS y SQS (patrón de mensajería asíncrona).

Un evento lleva un identificador único y estable: el consumidor lo usa para no repetir una
operación financiera si el mensaje llega dos veces (entrega duplicada de SQS, o un reenvío del
barrido de pendientes). Por eso el identificador se deriva del hecho de negocio y no se genera
al azar.
"""

import json
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TipoEvento(str, Enum):
    SINIESTRO_PARAMETRICO_APROBADO = "SINIESTRO_PARAMETRICO_APROBADO"


class EventoNegocio(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evento_id: str = Field(min_length=1, max_length=120)
    tipo: TipoEvento
    ocurrido_en: datetime
    datos: dict[str, str]

    def como_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def desde_cuerpo(cls, cuerpo: str) -> "EventoNegocio":
        """Lee el cuerpo de un mensaje de SQS.

        Con la entrega cruda de SNS el cuerpo es el evento. Si la suscripción no la usara, SNS
        envuelve el evento en un sobre (`Type: Notification` y `Message`): se desenvuelve aquí.
        """
        contenido = json.loads(cuerpo)
        if isinstance(contenido, dict) and contenido.get("Type") == "Notification":
            contenido = json.loads(contenido["Message"])
        return cls.model_validate(contenido)
