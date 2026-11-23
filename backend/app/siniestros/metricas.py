"""Métricas de la telemetría paramétrica en CloudWatch (HU20, EC — observabilidad).

Publica contadores en el namespace `Solventa/Telemetria`:

- `EventosRecibidos`: eventos aceptados por la ingesta (al publicarlos en la cola).
- `EventosProcesados`: eventos que el worker evaluó con éxito.
- `EventosFallidos`: eventos cuyo procesamiento falló (vuelven a la cola y, tras los reintentos,
  acaban en la DLQ por la redrive policy).

La profundidad de la cola NO se publica aquí: SQS ya expone `ApproximateNumberOfMessagesVisible`
(pendientes) y `ApproximateNumberOfMessagesNotVisible` (en vuelo) de forma nativa en CloudWatch.

Es tolerante a fallos por diseño: si CloudWatch no responde, se registra y se continúa; una
métrica nunca debe tumbar la ingesta ni el worker. Se desactiva con `EC_METRICAS=false`.
"""

import logging
import os

logger = logging.getLogger(__name__)

NAMESPACE = "Solventa/Telemetria"

EVENTOS_RECIBIDOS = "EventosRecibidos"
EVENTOS_PROCESADOS = "EventosProcesados"
EVENTOS_FALLIDOS = "EventosFallidos"


def metricas_activas() -> bool:
    return os.getenv("EC_METRICAS", "true").strip().lower() != "false"


class MetricasTelemetria:
    """Emisor de métricas a CloudWatch. El cliente boto3 se crea de forma perezosa."""

    def __init__(self, cliente=None):
        self._cliente = cliente

    def _cloudwatch(self):
        if self._cliente is None:
            import boto3

            self._cliente = boto3.client(
                "cloudwatch", region_name=os.getenv("AWS_DEFAULT_REGION")
            )
        return self._cliente

    def contar(self, metrica: str, valor: float = 1.0) -> None:
        """Suma `valor` a `metrica`. Nunca lanza: tolera que CloudWatch no responda."""
        if not metricas_activas():
            return
        try:
            self._cloudwatch().put_metric_data(
                Namespace=NAMESPACE,
                MetricData=[{"MetricName": metrica, "Value": valor, "Unit": "Count"}],
            )
        except Exception as error:  # noqa: BLE001 — observabilidad best-effort.
            logger.warning("No se pudo publicar la métrica %s: %s", metrica, error)
