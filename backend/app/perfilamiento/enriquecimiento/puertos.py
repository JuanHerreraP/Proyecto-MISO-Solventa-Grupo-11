"""Puertos del enriquecimiento.

`FuenteExterna` es el adaptador estándar de EC14: para sumar un agregador de Open Finance o
una fuente de Open Data se escribe una clase que cumpla este puerto y se registra en la
configuración. El servicio de enriquecimiento y sus consumidores no cambian.
"""

from datetime import datetime
from typing import Protocol

from app.perfilamiento.dominio.modelos import SenalesOpenData, SenalesOpenFinance
from app.perfilamiento.enriquecimiento.modelos import Consentimiento, TipoFuente

SenalesFuente = SenalesOpenFinance | SenalesOpenData


class FuenteNoDisponible(Exception):
    """La fuente no respondió a tiempo, respondió con error o con un contenido inválido."""

    def __init__(self, proveedor: str, motivo: str):
        super().__init__(f"{proveedor}: {motivo}")
        self.proveedor = proveedor
        self.motivo = motivo


class FuenteExterna(Protocol):
    tipo: TipoFuente
    proveedor: str

    async def consultar(self, cliente_id: str) -> SenalesFuente:
        """Devuelve las señales en el modelo interno o lanza `FuenteNoDisponible`."""
        ...


class CacheSenales(Protocol):
    def guardar(
        self, cliente_id: str, tipo: TipoFuente, senales: SenalesFuente, obtenido_en: datetime
    ) -> None: ...

    def obtener(
        self, cliente_id: str, tipo: TipoFuente
    ) -> tuple[SenalesFuente, datetime] | None: ...


class RepositorioConsentimientos(Protocol):
    def registrar(self, consentimiento: Consentimiento) -> None: ...

    def vigente(self, cliente_id: str, ahora: datetime) -> Consentimiento | None: ...
