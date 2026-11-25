"""Almacén de eventos del proveedor simulado de telemetría (HU20).

El proveedor corre como contenedor acompañante (sidecar) dentro de CADA tarea del backend. Hay
varias réplicas del backend, así que hay varias instancias del proveedor. Si cada una guardara los
eventos solo en su memoria, `GET /events` y `POST /simulate/retry/{id}` darían resultados distintos
según la réplica que atienda la petición.

Para dar una vista consistente entre réplicas se reutiliza el Redis existente (ElastiCache en AWS):
cuando hay `REDIS_URL`, los eventos y sus resultados se guardan ahí. Sin `REDIS_URL` (desarrollo
local y pruebas) se usa un almacén en memoria del proceso, con el mismo comportamiento.

Regla de diseño heredada de `redis_cliente`: un fallo de Redis no debe tumbar el proveedor. Las
escrituras que fallan se registran y se omiten; las lecturas que fallan devuelven "no hay".
"""

from __future__ import annotations

import logging
import os
from typing import Protocol

from mocks.telemetry.modelos import EventoTelemetria, RespuestaSimulacion

logger = logging.getLogger(__name__)

# Los eventos del proveedor son efímeros (demo de idempotencia y consulta); no deben vivir para
# siempre en Redis. Una vigencia amplia cubre una sesión de demostración sin acumular basura.
VIGENCIA_SEGUNDOS = 24 * 60 * 60
PREFIJO = "telemetry:mock"


class AlmacenEventos(Protocol):
    """Guarda el evento generado y su resultado, y permite consultarlos por réplica cualquiera."""

    def guardar(self, evento: EventoTelemetria, resultado: RespuestaSimulacion) -> None: ...

    def obtener_evento(self, evento_id: str) -> EventoTelemetria | None: ...

    def listar_resultados(self) -> list[RespuestaSimulacion]: ...


class AlmacenEnMemoria:
    """Almacén por proceso para desarrollo local y pruebas (sin Redis)."""

    def __init__(self) -> None:
        self._eventos: dict[str, EventoTelemetria] = {}
        self._resultados: dict[str, RespuestaSimulacion] = {}

    def guardar(self, evento: EventoTelemetria, resultado: RespuestaSimulacion) -> None:
        self._eventos[evento.evento_id] = evento
        self._resultados[evento.evento_id] = resultado

    def obtener_evento(self, evento_id: str) -> EventoTelemetria | None:
        return self._eventos.get(evento_id)

    def listar_resultados(self) -> list[RespuestaSimulacion]:
        return list(self._resultados.values())

    def limpiar(self) -> None:
        """Solo para pruebas: deja el almacén vacío entre casos."""
        self._eventos.clear()
        self._resultados.clear()


class AlmacenRedis:
    """Almacén compartido entre réplicas sobre el Redis existente.

    Cada evento se guarda bajo `telemetry:mock:evento:<id>` y su resultado bajo
    `telemetry:mock:resultado:<id>`. El conjunto `telemetry:mock:ids` indexa los identificadores
    para poder listarlos sin recorrer todas las claves de Redis.
    """

    def __init__(self, cliente) -> None:
        self._cliente = cliente

    def _clave_evento(self, evento_id: str) -> str:
        return f"{PREFIJO}:evento:{evento_id}"

    def _clave_resultado(self, evento_id: str) -> str:
        return f"{PREFIJO}:resultado:{evento_id}"

    @property
    def _clave_indice(self) -> str:
        return f"{PREFIJO}:ids"

    def guardar(self, evento: EventoTelemetria, resultado: RespuestaSimulacion) -> None:
        try:
            tuberia = self._cliente.pipeline()
            tuberia.set(
                self._clave_evento(evento.evento_id),
                evento.model_dump_json(),
                ex=VIGENCIA_SEGUNDOS,
            )
            tuberia.set(
                self._clave_resultado(evento.evento_id),
                resultado.model_dump_json(),
                ex=VIGENCIA_SEGUNDOS,
            )
            tuberia.sadd(self._clave_indice, evento.evento_id)
            tuberia.expire(self._clave_indice, VIGENCIA_SEGUNDOS)
            tuberia.execute()
        except Exception as error:  # noqa: BLE001 — Redis caído no debe romper el proveedor.
            logger.warning("Redis no guardó el evento %s: %s", evento.evento_id, error)

    def obtener_evento(self, evento_id: str) -> EventoTelemetria | None:
        try:
            crudo = self._cliente.get(self._clave_evento(evento_id))
        except Exception as error:  # noqa: BLE001
            logger.warning("Redis no leyó el evento %s: %s", evento_id, error)
            return None
        if not crudo:
            return None
        return EventoTelemetria.model_validate_json(crudo)

    def listar_resultados(self) -> list[RespuestaSimulacion]:
        try:
            ids = self._cliente.smembers(self._clave_indice)
        except Exception as error:  # noqa: BLE001
            logger.warning("Redis no listó los eventos: %s", error)
            return []
        resultados: list[RespuestaSimulacion] = []
        for evento_id in sorted(ids):
            try:
                crudo = self._cliente.get(self._clave_resultado(evento_id))
            except Exception as error:  # noqa: BLE001
                logger.warning("Redis no leyó el resultado %s: %s", evento_id, error)
                continue
            if crudo:
                resultados.append(RespuestaSimulacion.model_validate_json(crudo))
        return resultados


def _crear_cliente_redis(url: str):
    import redis

    return redis.Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=1.0,
        socket_timeout=1.0,
        health_check_interval=30,
    )


def construir_almacen() -> AlmacenEventos:
    """Elige el almacén por entorno: Redis si hay `REDIS_URL`, si no en memoria."""
    url = os.getenv("REDIS_URL")
    if url:
        try:
            return AlmacenRedis(_crear_cliente_redis(url))
        except Exception as error:  # noqa: BLE001 — si Redis no se puede crear, se usa memoria.
            logger.warning("No se pudo crear el cliente Redis (%s); se usa memoria.", error)
    return AlmacenEnMemoria()
