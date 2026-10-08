"""Puerto de persistencia y adaptador en memoria para socios."""

from typing import Protocol

from app.socios.dominio.modelos import SocioDistribucion


class RepositorioSocios(Protocol):
    def guardar(self, socio: SocioDistribucion) -> None: ...

    def obtener(self, socio_id: str) -> SocioDistribucion | None: ...

    def obtener_por_nit(self, nit: str) -> SocioDistribucion | None: ...


class RepositorioSociosEnMemoria:
    def __init__(self):
        self._por_id: dict[str, SocioDistribucion] = {}
        self._id_por_nit: dict[str, str] = {}

    def guardar(self, socio: SocioDistribucion) -> None:
        self._por_id[socio.socio_id] = socio
        self._id_por_nit[socio.nit] = socio.socio_id

    def obtener(self, socio_id: str) -> SocioDistribucion | None:
        return self._por_id.get(socio_id)

    def obtener_por_nit(self, nit: str) -> SocioDistribucion | None:
        socio_id = self._id_por_nit.get(nit)
        return self._por_id.get(socio_id) if socio_id is not None else None
