"""Armado del servicio de notificaciones para quien lo necesita (HU05).

Los flujos de negocio (la evaluación de siniestros, el job de vencimientos) reciben un
`ServicioNotificaciones` ya armado, con la base de datos de la petición y el canal de push
configurado. El canal es uno solo por proceso: se crea la primera vez y se reutiliza, para no
pedirle a Google un token de acceso nuevo en cada envío.
"""

import logging
from functools import lru_cache

from sqlalchemy.orm import Session

from app.notificaciones.canal import ConfiguracionPushInvalida, EnviadorPush, crear_enviador_push
from app.notificaciones.repositorio import (
    RepositorioDispositivosPostgres,
    RepositorioNotificacionesPostgres,
    RepositorioPreferenciasPostgres,
)
from app.notificaciones.servicio import ServicioNotificaciones

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def enviador_push() -> EnviadorPush | None:
    """El canal de push del proceso, o None si está mal configurado.

    Una credencial mala no debe tumbar la aprobación de un siniestro: se avisa en el log (una
    sola vez) y las notificaciones se siguen registrando en la bandeja, sin push.
    """
    try:
        return crear_enviador_push()
    except ConfiguracionPushInvalida as error:
        logger.error("Push deshabilitado por configuración inválida: %s", error)
        return None


def crear_servicio_notificaciones(db: Session) -> ServicioNotificaciones:
    return ServicioNotificaciones(
        notificaciones=RepositorioNotificacionesPostgres(db),
        dispositivos=RepositorioDispositivosPostgres(db),
        preferencias=RepositorioPreferenciasPostgres(db),
        enviador=enviador_push(),
    )
