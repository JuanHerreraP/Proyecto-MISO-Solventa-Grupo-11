"""Worker que consume la cola SQS de pagos automáticos (patrón de mensajería asíncrona).

Hace long polling sobre la cola (`SQS_PAGOS_QUEUE_URL`), ordena el desembolso de cada evento con
`ConsumidorPagos` y borra el mensaje SOLO si el procesamiento fue exitoso. Los mensajes que
fallan no se borran: SQS los vuelve visibles al vencer el visibility timeout y, tras agotar los
reintentos, la redrive policy los manda a la DLQ. Así ningún pago se pierde en silencio.

Además, cada cierto tiempo hace el barrido de pendientes: vuelve a publicar los pagos que
quedaron sin ordenar (ver `barrido.py`).

Variables de entorno:
    SQS_PAGOS_QUEUE_URL            Cola de pagos (obligatoria).
    SNS_TOPIC_ARN                  Tópico donde el barrido republica (sin él, no hay barrido).
    PAGOS_WORKER_CONCURRENCIA      Mensajes en paralelo (por defecto 4).
    PAGOS_BARRIDO_SEGUNDOS         Cada cuánto corre el barrido (por defecto 300).
    PAGOS_BARRIDO_ANTIGUEDAD       Segundos sin actividad para considerar un pago pendiente
                                   (por defecto 300).
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from app.api.desembolsos import construir_desembolsos
from app.desembolsos.barrido import barrer_pendientes
from app.desembolsos.consumidor import ConsumidorPagos, ResultadoConsumo
from app.desembolsos.pendientes import RepositorioPendientesPagoPostgres
from app.eventos.modelos import EventoNegocio
from app.eventos.procesados import EventoProcesadoDB, RepositorioEventosProcesadosPostgres
from app.eventos.publicador import PublicadorNegocio, publicador_negocio
from app.infraestructura.database import SessionLocal, engine
from app.siniestros.repositorio import RepositorioSiniestrosPostgres

logger = logging.getLogger(__name__)


def _entero(nombre: str, por_defecto: int) -> int:
    try:
        return max(1, int(os.getenv(nombre, str(por_defecto))))
    except ValueError:
        return por_defecto


def concurrencia() -> int:
    return _entero("PAGOS_WORKER_CONCURRENCIA", 4)


def procesar_mensaje(cuerpo: str) -> ResultadoConsumo:
    """Procesa un mensaje en su propia sesión de base de datos.

    Lanza si el procesamiento falla, para que el llamador NO borre el mensaje y SQS lo reintente.
    """
    evento = EventoNegocio.desde_cuerpo(cuerpo)
    db = SessionLocal()
    try:
        consumidor = ConsumidorPagos(
            desembolsos=construir_desembolsos(db),
            siniestros=RepositorioSiniestrosPostgres(db),
            procesados=RepositorioEventosProcesadosPostgres(db),
        )
        return consumidor.procesar(evento)
    finally:
        db.close()


def _consumir_lote(sqs, url_cola: str, ejecutor) -> None:
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
            procesar_mensaje(mensaje["Body"])
        except Exception:  # noqa: BLE001 — el mensaje fallido se reintenta; no se borra.
            logger.exception("Fallo al procesar un pago; no se borra, se reintentará.")
            return
        # Solo se borra lo que se procesó bien: el resto vuelve a la cola y acaba en la DLQ.
        try:
            sqs.delete_message(QueueUrl=url_cola, ReceiptHandle=mensaje["ReceiptHandle"])
        except Exception:  # noqa: BLE001 — si no se puede borrar, se reprocesará (idempotente).
            logger.exception("No se pudo borrar un pago ya procesado; se reprocesará.")

    list(ejecutor.map(trabajar, mensajes))


def barrer(publicador: PublicadorNegocio, ahora: datetime | None = None) -> int:
    """Corre un barrido de pendientes en su propia sesión."""
    ahora = ahora or datetime.now(UTC)
    antes_de = ahora - timedelta(seconds=_entero("PAGOS_BARRIDO_ANTIGUEDAD", 300))
    db = SessionLocal()
    try:
        return barrer_pendientes(
            RepositorioPendientesPagoPostgres(db),
            RepositorioSiniestrosPostgres(db),
            publicador,
            antes_de,
        )
    finally:
        db.close()


def _preparar_esquema() -> None:
    """Crea la tabla de eventos procesados si aún no existe (la API la crea al arrancar)."""
    EventoProcesadoDB.__table__.create(bind=engine, checkfirst=True)


def ejecutar(parar=lambda: False) -> None:
    """Loop principal del worker. `parar` permite cortar el bucle en pruebas."""
    url_cola = os.getenv("SQS_PAGOS_QUEUE_URL")
    if not url_cola:
        raise ValueError(
            "SQS_PAGOS_QUEUE_URL no está definido: el worker no tiene cola que consumir."
        )

    import boto3

    _preparar_esquema()
    sqs = boto3.client("sqs", region_name=os.getenv("AWS_DEFAULT_REGION"))
    publicador = publicador_negocio()
    if publicador is None:
        logger.warning("SNS_TOPIC_ARN no está definido: el worker no hará barrido de pendientes.")
    cada = _entero("PAGOS_BARRIDO_SEGUNDOS", 300)
    siguiente_barrido = time.monotonic() + cada
    logger.info("Worker de pagos iniciado. Cola=%s", url_cola)
    with ThreadPoolExecutor(max_workers=concurrencia()) as ejecutor:
        while not parar():
            try:
                _consumir_lote(sqs, url_cola, ejecutor)
            except Exception:  # noqa: BLE001 — ningún fallo transitorio debe matar el worker.
                logger.exception("Error en el ciclo de consumo; se continúa.")
            if publicador is not None and time.monotonic() >= siguiente_barrido:
                siguiente_barrido = time.monotonic() + cada
                try:
                    barrer(publicador)
                except Exception:  # noqa: BLE001 — el barrido es de mejor esfuerzo.
                    logger.exception("Error en el barrido de pendientes; se continúa.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ejecutar()
