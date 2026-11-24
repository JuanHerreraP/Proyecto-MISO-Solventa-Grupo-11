"""Adaptadores de Redis para el enriquecimiento (patrón Cache-Aside).

- `CacheSenalesRedis`: las señales de cada fuente externa por cliente. Con ella, el servicio
  consulta primero la caché y llama al proveedor solo si no hay un dato fresco; y si el
  proveedor falla, usa el último dato vigente.
- `UltimosResultadosRedis`: el último resultado consolidado de cada cliente, para que lo vea
  cualquier réplica (antes vivía en la memoria de un solo proceso).

Si Redis no responde o el dato guardado no se puede leer, se trata como "no hay": nunca rompe
una cotización.
"""

import json
import logging
from datetime import datetime, timedelta

from app.infraestructura.redis_cliente import AlmacenRedis
from app.perfilamiento.dominio.modelos import SenalesOpenData, SenalesOpenFinance
from app.perfilamiento.enriquecimiento.memoria import VIGENCIA_CACHE
from app.perfilamiento.enriquecimiento.modelos import ResultadoEnriquecimiento, TipoFuente
from app.perfilamiento.enriquecimiento.puertos import SenalesFuente

logger = logging.getLogger(__name__)

MODELO_POR_FUENTE: dict[TipoFuente, type[SenalesFuente]] = {
    TipoFuente.OPEN_FINANCE: SenalesOpenFinance,
    TipoFuente.OPEN_DATA: SenalesOpenData,
}


class CacheSenalesRedis:
    def __init__(self, almacen: AlmacenRedis, vigencia: timedelta = VIGENCIA_CACHE):
        self._almacen = almacen
        self._vigencia = vigencia

    @staticmethod
    def _clave(cliente_id: str, tipo: TipoFuente) -> str:
        return f"{tipo.value}:{cliente_id}"

    def guardar(
        self, cliente_id: str, tipo: TipoFuente, senales: SenalesFuente, obtenido_en: datetime
    ) -> None:
        contenido = json.dumps(
            {"obtenido_en": obtenido_en.isoformat(), "senales": senales.model_dump(mode="json")}
        )
        self._almacen.guardar(
            self._clave(cliente_id, tipo), contenido, int(self._vigencia.total_seconds())
        )

    def obtener(self, cliente_id: str, tipo: TipoFuente) -> tuple[SenalesFuente, datetime] | None:
        bruto = self._almacen.obtener(self._clave(cliente_id, tipo))
        if bruto is None:
            return None
        try:
            datos = json.loads(bruto)
            obtenido_en = datetime.fromisoformat(datos["obtenido_en"])
            senales = MODELO_POR_FUENTE[tipo].model_validate(datos["senales"])
        except (ValueError, KeyError, TypeError):
            # Un dato ilegible (por ejemplo, de una versión anterior del modelo) no se usa.
            logger.warning("Dato de caché ilegible: %s; se ignora", self._clave(cliente_id, tipo))
            return None
        return senales, obtenido_en


class UltimosResultadosRedis:
    def __init__(self, almacen: AlmacenRedis, vigencia: timedelta = VIGENCIA_CACHE):
        self._almacen = almacen
        self._vigencia = vigencia

    def guardar(self, cliente_id: str, resultado: ResultadoEnriquecimiento) -> None:
        self._almacen.guardar(
            cliente_id, resultado.model_dump_json(), int(self._vigencia.total_seconds())
        )

    def obtener(self, cliente_id: str) -> ResultadoEnriquecimiento | None:
        bruto = self._almacen.obtener(cliente_id)
        if bruto is None:
            return None
        try:
            return ResultadoEnriquecimiento.model_validate_json(bruto)
        except ValueError:
            logger.warning("Resultado ilegible en Redis para %s; se ignora", cliente_id)
            return None
