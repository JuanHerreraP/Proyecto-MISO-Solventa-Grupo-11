"""Redis compartido entre réplicas: caché y estado temporal (patrón Cache-Aside).

Con más de una réplica del backend, lo que cada proceso guardara en su memoria (perfiles,
señales de las fuentes externas, el último resultado de un enriquecimiento) lo vería solo esa
réplica. Redis (ElastiCache en AWS) lo comparte.

Sin `REDIS_URL` no hay Redis y cada componente conserva su adaptador en memoria, que es el
modo de desarrollo local y de las pruebas.

Regla de diseño: **un fallo de Redis nunca rompe la operación del cliente**. Se trata como un
fallo de caché: la lectura devuelve "no hay" y la escritura se omite, con un aviso en el log.
"""

import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

SEGUNDOS_CONEXION = 1.0
SEGUNDOS_OPERACION = 1.0


def crear_cliente_redis(url: str):
    """Crea el cliente. Las URL `rediss://` usan TLS (cifrado en tránsito)."""
    import redis

    return redis.Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=SEGUNDOS_CONEXION,
        socket_timeout=SEGUNDOS_OPERACION,
        health_check_interval=30,
    )


@lru_cache(maxsize=1)
def cliente_redis():
    """El cliente del proceso, o None si no hay `REDIS_URL` configurada."""
    url = os.getenv("REDIS_URL")
    return crear_cliente_redis(url) if url else None


class AlmacenRedis:
    """Guarda texto bajo una clave, con vencimiento. Tolera que Redis no responda."""

    def __init__(self, cliente, prefijo: str):
        self._cliente = cliente
        self._prefijo = prefijo

    def _clave(self, clave: str) -> str:
        return f"{self._prefijo}:{clave}"

    def guardar(self, clave: str, valor: str, vigencia_segundos: int) -> bool:
        try:
            self._cliente.set(self._clave(clave), valor, ex=max(1, int(vigencia_segundos)))
        except Exception as error:  # noqa: BLE001 — Redis caído no debe romper la operación.
            logger.warning("Redis no guardó %s: %s", self._clave(clave), _describir(error))
            return False
        return True

    def obtener(self, clave: str) -> str | None:
        try:
            return self._cliente.get(self._clave(clave))
        except Exception as error:  # noqa: BLE001
            logger.warning("Redis no leyó %s: %s", self._clave(clave), _describir(error))
            return None

    def eliminar(self, clave: str) -> None:
        try:
            self._cliente.delete(self._clave(clave))
        except Exception as error:  # noqa: BLE001
            logger.warning("Redis no eliminó %s: %s", self._clave(clave), _describir(error))


def _describir(error: Exception) -> str:
    return type(error).__name__
