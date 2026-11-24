"""Consumidor de pagos automáticos (patrón de mensajería asíncrona, consumidor idempotente).

Recibe el evento `SINIESTRO_PARAMETRICO_APROBADO` que Siniestros publicó en SNS y ordena el
desembolso del siniestro. Es idempotente en dos niveles:

1. Antes de pagar pregunta si ese evento ya se procesó.
2. El desembolso es único por siniestro en la base: aunque dos consumidores lean el mismo
   evento a la vez, o el evento se republique, nunca se paga dos veces.

Cuando algo falla, lanza una excepción para que el llamador no borre el mensaje: SQS lo vuelve a
entregar y, tras agotar los reintentos, lo manda a la cola de mensajes fallidos (DLQ).
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum

from app.desembolsos.modelos import EstadoDesembolso
from app.desembolsos.servicio import ServicioDesembolsos
from app.eventos.modelos import EventoNegocio, TipoEvento
from app.eventos.procesados import RepositorioEventosProcesados
from app.siniestros.repositorio import RepositorioSiniestros

logger = logging.getLogger(__name__)

CONSUMIDOR = "pagos"


class ResultadoConsumo(str, Enum):
    PAGADO = "PAGADO"
    DUPLICADO = "DUPLICADO"
    IGNORADO = "IGNORADO"


class SiniestroDelEventoNoEncontrado(Exception):
    """El evento apunta a un siniestro que no existe: no hay nada que pagar."""


class DesembolsoPendiente(Exception):
    """La red de desembolsos no respondió: el pago queda pendiente y el mensaje se reintenta."""


class ConsumidorPagos:
    def __init__(
        self,
        desembolsos: ServicioDesembolsos,
        siniestros: RepositorioSiniestros,
        procesados: RepositorioEventosProcesados,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self._desembolsos = desembolsos
        self._siniestros = siniestros
        self._procesados = procesados
        self._reloj = reloj

    def procesar(self, evento: EventoNegocio) -> ResultadoConsumo:
        if evento.tipo is not TipoEvento.SINIESTRO_PARAMETRICO_APROBADO:
            logger.info("Evento %s de tipo %s: no es de pagos", evento.evento_id, evento.tipo)
            return ResultadoConsumo.IGNORADO

        if self._procesados.ya_procesado(evento.evento_id, CONSUMIDOR):
            logger.info("Evento %s ya procesado: se omite", evento.evento_id)
            return ResultadoConsumo.DUPLICADO

        siniestro_id = evento.datos["siniestro_id"]
        siniestro = self._siniestros.obtener(siniestro_id)
        if siniestro is None:
            raise SiniestroDelEventoNoEncontrado(siniestro_id)

        # Idempotente por siniestro: repetirla devuelve el mismo desembolso, sin pagar otra vez.
        desembolso = self._desembolsos.desembolsar(siniestro)
        if desembolso.estado is EstadoDesembolso.PENDIENTE:
            # El evento NO se marca como procesado: el reintento de SQS debe volver a intentarlo.
            raise DesembolsoPendiente(desembolso.desembolso_id)
        if desembolso.estado is EstadoDesembolso.FALLIDA:
            # Es definitivo para este evento (por ejemplo, cuenta inexistente). Operaciones lo
            # reintenta desde su bandeja cuando el cliente corrija su cuenta.
            logger.warning(
                "Desembolso %s del siniestro %s FALLIDO: %s",
                desembolso.desembolso_id,
                siniestro_id,
                desembolso.motivo_fallo,
            )

        self._procesados.marcar(evento.evento_id, CONSUMIDOR, self._reloj())
        return ResultadoConsumo.PAGADO
