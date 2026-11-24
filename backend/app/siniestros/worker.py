"""Worker que consume los eventos de telemetría de la cola (HU20, EC — contrapresión).

Hace long polling sobre la cola SQS (`SQS_QUEUE_URL`), procesa cada mensaje con
`ServicioTelemetria` y borra el mensaje SOLO si el procesamiento fue exitoso. Los mensajes que
fallan no se borran: SQS los vuelve visibles al vencer el visibility timeout y, tras agotar los
reintentos, la redrive policy los manda a la DLQ. Así ningún evento se pierde en silencio.

Concurrencia acotada con un `ThreadPoolExecutor` (`EC_WORKER_CONCURRENCIA`, por defecto 4) para no
saturar la base ni la red de desembolsos. Cada mensaje usa su propia `Session` de base de datos y
la cierra siempre.

Desembolso configurable (`EC_ORDENAR_DESEMBOLSO`, por defecto `false`):

- `false`: el worker procesa con `al_crear=None`. Crea el siniestro paramétrico pero NO ordena el
  desembolso ni marca pago ejecutado. Pensado para el MVP de contrapresión, donde el pago se
  decide en otro paso.
- `true`: usa `construir_evaluacion(db).aprobar_automatico`: aprueba el siniestro y avisa al
  cliente. Sin `SNS_TOPIC_ARN` ordena además el desembolso en el mismo proceso (el flujo
  síncrono de HU15). Con `SNS_TOPIC_ARN` publica el evento de pago en SNS y lo ordena el worker
  de pagos (`app/desembolsos/worker.py`).

El loop es robusto: una excepción en un mensaje se registra y no mata el worker.
"""

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from app.api.desembolsos import construir_evaluacion
from app.infraestructura.database import SessionLocal
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.siniestros.metricas import EVENTOS_FALLIDOS, EVENTOS_PROCESADOS, MetricasTelemetria
from app.siniestros.repositorio import RepositorioSiniestrosPostgres
from app.siniestros.telemetria import EventoParametrico, ServicioTelemetria

logger = logging.getLogger(__name__)


def ordenar_desembolso() -> bool:
    return os.getenv("EC_ORDENAR_DESEMBOLSO", "false").strip().lower() == "true"


def concurrencia() -> int:
    try:
        return max(1, int(os.getenv("EC_WORKER_CONCURRENCIA", "4")))
    except ValueError:
        return 4


def procesar_mensaje(cuerpo: str, metricas: MetricasTelemetria | None = None) -> None:
    """Procesa un mensaje de la cola en su propia sesión de base de datos.

    Lanza si el procesamiento falla, para que el llamador NO borre el mensaje y SQS lo reintente.
    """
    datos = json.loads(cuerpo)
    evento = EventoParametrico(
        evento_id=datos["evento_id"],
        tipo_evento=datos["tipo_evento"],
        valor_observado=datos["valor_observado"],
        fecha_evento=datos["fecha_evento"],
        numero_vuelo=datos.get("numero_vuelo"),
        ubicacion=datos.get("ubicacion"),
    )
    db = SessionLocal()
    try:
        al_crear = construir_evaluacion(db).aprobar_automatico if ordenar_desembolso() else None
        servicio = ServicioTelemetria(
            siniestros=RepositorioSiniestrosPostgres(db),
            polizas=RepositorioPolizasPostgres(db),
            al_crear=al_crear,
        )
        servicio.procesar(evento)
    finally:
        db.close()
    if metricas is not None:
        metricas.contar(EVENTOS_PROCESADOS)


def _consumir_lote(sqs, url_cola: str, ejecutor, metricas: MetricasTelemetria) -> None:
    respuesta = sqs.receive_message(
        QueueUrl=url_cola,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=20,
    )
    mensajes = respuesta.get("Messages", [])
    if not mensajes:
        return

    def trabajar(mensaje: dict) -> None:
        try:
            procesar_mensaje(mensaje["Body"], metricas)
        except Exception:  # noqa: BLE001 — el mensaje fallido se reintenta; no se borra.
            logger.exception("Fallo al procesar mensaje; no se borra, se reintentará.")
            if metricas is not None:
                metricas.contar(EVENTOS_FALLIDOS)
            return
        # Solo se borra lo que se procesó bien: el resto vuelve a la cola y acaba en la DLQ.
        try:
            sqs.delete_message(QueueUrl=url_cola, ReceiptHandle=mensaje["ReceiptHandle"])
        except Exception:  # noqa: BLE001 — si no se puede borrar, se reprocesará (idempotente).
            logger.exception("No se pudo borrar un mensaje ya procesado; se reprocesará.")

    # map() agota el lote antes de volver; una excepción en un worker no mata el loop
    # porque trabajar() las captura.
    list(ejecutor.map(trabajar, mensajes))


def ejecutar(parar=lambda: False) -> None:
    """Loop principal del worker. `parar` permite cortar el bucle en pruebas."""
    url_cola = os.getenv("SQS_QUEUE_URL")
    if not url_cola:
        raise ValueError("SQS_QUEUE_URL no está definido: el worker no tiene cola que consumir.")

    import boto3

    sqs = boto3.client("sqs", region_name=os.getenv("AWS_DEFAULT_REGION"))
    metricas = MetricasTelemetria()
    logger.info("Worker de telemetría iniciado. Cola=%s", url_cola)
    with ThreadPoolExecutor(max_workers=concurrencia()) as ejecutor:
        while not parar():
            try:
                _consumir_lote(sqs, url_cola, ejecutor, metricas)
            except Exception:  # noqa: BLE001 — ningún fallo transitorio debe matar el worker.
                logger.exception("Error en el ciclo de consumo; se continúa.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ejecutar()
