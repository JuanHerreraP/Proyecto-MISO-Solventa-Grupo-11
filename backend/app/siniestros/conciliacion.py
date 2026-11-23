"""Conciliación de la telemetría paramétrica (HU20, EC — contrapresión).

Demuestra que no se pierde ni se duplica ningún evento aceptado. La identidad que se busca
sostener es:

    aceptados == procesados + en_cola + en_dlq

donde:

- `aceptados`: eventos que la ingesta confirmó (contador/métrica `EventosRecibidos`).
- `procesados`: siniestros originados por telemetría en la base (creados, sin cobertura y
  duplicados; en el MVP se cuentan los siniestros con `registrado_por = 'TELEMETRIA'`).
- `en_cola`: `ApproximateNumberOfMessages` (+ `NotVisible`, en vuelo) de la cola principal.
- `en_dlq`: `ApproximateNumberOfMessages` de la cola de mensajes fallidos.

La profundidad de la cola la expone SQS de forma nativa; aquí solo se lee para conciliar.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.siniestros.modelos_db import SiniestroDB

ORIGEN_TELEMETRIA = "TELEMETRIA"


@dataclass
class Conciliacion:
    """Fotografía de los conteos para la identidad de conciliación."""

    procesados_bd: int
    en_cola: int
    en_vuelo: int
    en_dlq: int

    @property
    def total_observado(self) -> int:
        """Procesados + lo que aún está en el sistema de colas (cola principal y DLQ)."""
        return self.procesados_bd + self.en_cola + self.en_vuelo + self.en_dlq

    def cuadra(self, aceptados: int) -> bool:
        """Verdadero si los eventos aceptados por la ingesta están todos contabilizados."""
        return aceptados == self.total_observado


def contar_siniestros_telemetria(db: Session) -> int:
    """Siniestros originados por telemetría en la base (`registrado_por = 'TELEMETRIA'`)."""
    sentencia = (
        select(func.count())
        .select_from(SiniestroDB)
        .where(SiniestroDB.registrado_por == ORIGEN_TELEMETRIA)
    )
    return int(db.scalar(sentencia) or 0)


def _atributos_cola(sqs, url_cola: str) -> dict[str, str]:
    respuesta = sqs.get_queue_attributes(
        QueueUrl=url_cola,
        AttributeNames=[
            "ApproximateNumberOfMessages",
            "ApproximateNumberOfMessagesNotVisible",
        ],
    )
    return respuesta.get("Attributes", {})


def conciliar(db: Session, sqs, url_cola: str, url_dlq: str | None) -> Conciliacion:
    """Construye la conciliación leyendo la base y los atributos de las colas SQS."""
    cola = _atributos_cola(sqs, url_cola)
    en_dlq = 0
    if url_dlq:
        dlq = _atributos_cola(sqs, url_dlq)
        en_dlq = int(dlq.get("ApproximateNumberOfMessages", 0))
    return Conciliacion(
        procesados_bd=contar_siniestros_telemetria(db),
        en_cola=int(cola.get("ApproximateNumberOfMessages", 0)),
        en_vuelo=int(cola.get("ApproximateNumberOfMessagesNotVisible", 0)),
        en_dlq=en_dlq,
    )
