"""Barrido de pagos pendientes: la red de seguridad de la mensajería asíncrona.

Publicar el evento y guardar la aprobación no son una sola operación. Si SNS no responde después
de aprobar, o los reintentos de la cola se agotan, el pago queda sin ordenar. El barrido busca
esos casos y vuelve a publicar su evento. Como el identificador del evento es el mismo, publicar
de más no puede pagar dos veces: el consumidor reconoce el evento repetido.
"""

import logging
from datetime import datetime

from app.desembolsos.pendientes import RepositorioPendientesPago
from app.eventos.publicador import PublicadorNegocio
from app.siniestros.eventos import evento_pago_parametrico
from app.siniestros.repositorio import RepositorioSiniestros

logger = logging.getLogger(__name__)


def barrer_pendientes(
    pendientes: RepositorioPendientesPago,
    siniestros: RepositorioSiniestros,
    publicador: PublicadorNegocio,
    antes_de: datetime,
    limite: int = 100,
) -> int:
    """Vuelve a publicar el pago de cada siniestro pendiente. Devuelve cuántos republicó."""
    republicados = 0
    for siniestro_id in pendientes.ids_pendientes(antes_de, limite):
        siniestro = siniestros.obtener(siniestro_id)
        if siniestro is None:
            continue
        try:
            publicador.publicar(evento_pago_parametrico(siniestro))
        except Exception:  # noqa: BLE001 — un fallo no detiene el barrido; el siguiente reintenta.
            logger.exception("No se pudo republicar el pago del siniestro %s", siniestro_id)
            continue
        republicados += 1
    if republicados:
        logger.info("Barrido de pagos: %d evento(s) republicado(s)", republicados)
    return republicados
