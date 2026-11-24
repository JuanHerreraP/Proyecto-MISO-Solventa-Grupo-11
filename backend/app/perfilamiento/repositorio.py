"""Puerto y adaptador para dejar el perfil disponible al motor de precios.

El adaptador en memoria sirve para desarrollo y pruebas. En despliegue se reemplaza por un
adaptador de ElastiCache Redis que implemente el mismo puerto (patrón Cache-Aside).
"""

import time
from typing import Protocol

from app.perfilamiento.dominio.modelos import PerfilRiesgo

VIGENCIA_PERFIL_SEGUNDOS = 3600


class RepositorioPerfiles(Protocol):
    def guardar(self, perfil: PerfilRiesgo) -> None: ...

    def obtener(self, cliente_id: str) -> PerfilRiesgo | None: ...


class RepositorioPerfilesEnMemoria:
    def __init__(self, vigencia_segundos: float = VIGENCIA_PERFIL_SEGUNDOS, reloj=time.monotonic):
        self._vigencia = vigencia_segundos
        self._reloj = reloj
        self._perfiles: dict[str, tuple[float, PerfilRiesgo]] = {}

    def guardar(self, perfil: PerfilRiesgo) -> None:
        self._perfiles[perfil.cliente_id] = (self._reloj() + self._vigencia, perfil)

    def obtener(self, cliente_id: str) -> PerfilRiesgo | None:
        registro = self._perfiles.get(cliente_id)
        if registro is None:
            return None
        vence, perfil = registro
        if self._reloj() >= vence:
            del self._perfiles[cliente_id]
            return None
        return perfil


class RepositorioPerfilesRedis:
    """Perfiles en Redis, visibles para todas las réplicas del backend (Cache-Aside).

    Si Redis falla, `obtener` devuelve None: el motor de precios cotiza con la tarifa base.
    """

    def __init__(self, almacen, vigencia_segundos: int = VIGENCIA_PERFIL_SEGUNDOS):
        self._almacen = almacen
        self._vigencia = vigencia_segundos

    def guardar(self, perfil: PerfilRiesgo) -> None:
        self._almacen.guardar(perfil.cliente_id, perfil.model_dump_json(), self._vigencia)

    def obtener(self, cliente_id: str) -> PerfilRiesgo | None:
        bruto = self._almacen.obtener(cliente_id)
        if bruto is None:
            return None
        try:
            return PerfilRiesgo.model_validate_json(bruto)
        except ValueError:
            return None
