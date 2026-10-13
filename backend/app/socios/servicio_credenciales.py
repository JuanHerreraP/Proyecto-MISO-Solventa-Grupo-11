"""Caso de uso para aprovisionar credenciales de integración a un socio."""

from collections.abc import Callable
from datetime import datetime

from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.dominio.credenciales import (
    CredencialesEmitidas,
    CredencialesSocio,
    generar_credenciales,
)
from app.socios.dominio.modelos import EstadoSocio
from app.socios.repositorio import RepositorioSocios
from app.socios.repositorio_credenciales import RepositorioCredencialesSocios
from app.socios.servicio import SocioInactivo, SocioNoEncontrado, ahora_utc

GeneradorCredenciales = Callable[
    [str, str, set[CodigoEndpoint], datetime],
    tuple[CredencialesSocio, str],
]


class ServicioCredencialesSocios:
    """Coordina la generación y persistencia segura de las credenciales."""

    def __init__(
        self,
        socios: RepositorioSocios,
        credenciales: RepositorioCredencialesSocios,
        reloj: Callable[[], datetime] = ahora_utc,
        generador: GeneradorCredenciales = generar_credenciales,
    ) -> None:
        self._socios = socios
        self._credenciales = credenciales
        self._reloj = reloj
        self._generador = generador

    def aprovisionar(self, socio_id: str) -> CredencialesEmitidas:
        socio = self._socios.obtener(socio_id)
        if socio is None:
            raise SocioNoEncontrado(socio_id)
        if socio.estado is not EstadoSocio.ACTIVO:
            raise SocioInactivo(socio_id)

        persistibles, client_secret = self._generador(
            socio.socio_id,
            socio.tenant_id,
            socio.endpoints_autorizados,
            self._reloj(),
        )
        self._credenciales.guardar(persistibles)

        return CredencialesEmitidas(
            socio_id=persistibles.socio_id,
            tenant_id=persistibles.tenant_id,
            client_id=persistibles.client_id,
            client_secret=client_secret,
            scopes=persistibles.scopes,
            creado_en=persistibles.creado_en,
        )
