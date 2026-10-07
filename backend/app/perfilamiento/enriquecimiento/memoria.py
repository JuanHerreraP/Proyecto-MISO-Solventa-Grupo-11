"""Adaptadores en memoria de la caché de señales y de los consentimientos.

Sirven para desarrollo y pruebas. En despliegue la caché se reemplaza por ElastiCache Redis
y los consentimientos por el servicio de Identidad, KYC y Consentimiento.
"""

from datetime import datetime, timedelta

from app.perfilamiento.enriquecimiento.modelos import Consentimiento, TipoFuente
from app.perfilamiento.enriquecimiento.puertos import SenalesFuente

VIGENCIA_CACHE = timedelta(hours=24)


class CacheSenalesEnMemoria:
    def __init__(self, vigencia: timedelta = VIGENCIA_CACHE, reloj=None):
        self._vigencia = vigencia
        self._reloj = reloj
        self._datos: dict[tuple[str, TipoFuente], tuple[SenalesFuente, datetime]] = {}

    def guardar(
        self, cliente_id: str, tipo: TipoFuente, senales: SenalesFuente, obtenido_en: datetime
    ) -> None:
        self._datos[(cliente_id, tipo)] = (senales, obtenido_en)

    def obtener(self, cliente_id: str, tipo: TipoFuente) -> tuple[SenalesFuente, datetime] | None:
        registro = self._datos.get((cliente_id, tipo))
        if registro is None:
            return None
        _, obtenido_en = registro
        ahora = self._reloj() if self._reloj else datetime.now(obtenido_en.tzinfo)
        if ahora - obtenido_en >= self._vigencia:
            del self._datos[(cliente_id, tipo)]
            return None
        return registro


class RepositorioConsentimientosEnMemoria:
    def __init__(self):
        self._por_cliente: dict[str, Consentimiento] = {}

    def registrar(self, consentimiento: Consentimiento) -> None:
        self._por_cliente[consentimiento.cliente_id] = consentimiento

    def vigente(self, cliente_id: str, ahora: datetime) -> Consentimiento | None:
        consentimiento = self._por_cliente.get(cliente_id)
        if consentimiento is None or consentimiento.vence_en <= ahora:
            return None
        return consentimiento
