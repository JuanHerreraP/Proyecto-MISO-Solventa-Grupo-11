"""Caso de uso para autenticar socios mediante client credentials."""

from collections.abc import Callable

from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.dominio.credenciales import (
    CredencialesSocio,
    TokenAccesoSocio,
    verificar_secret,
)
from app.socios.dominio.modelos import EstadoSocio
from app.socios.repositorio import RepositorioSocios
from app.socios.repositorio_credenciales import RepositorioCredencialesSocios
from app.socios.tokens import crear_access_token_socio

GeneradorToken = Callable[[CredencialesSocio, set[CodigoEndpoint]], tuple[str, int]]
VerificadorSecret = Callable[[str, CredencialesSocio], bool]


class CredencialesIntegracionInvalidas(Exception):
    """El client ID o el secreto no permiten autenticar al socio."""


class SocioIntegracionInactivo(Exception):
    """El socio asociado a las credenciales no se encuentra activo."""


class ServicioAutenticacionSocios:
    def __init__(
        self,
        socios: RepositorioSocios,
        credenciales: RepositorioCredencialesSocios,
        verificador: VerificadorSecret = verificar_secret,
        generador_token: GeneradorToken = crear_access_token_socio,
    ) -> None:
        self._socios = socios
        self._credenciales = credenciales
        self._verificador = verificador
        self._generador_token = generador_token

    def autenticar(self, client_id: str, client_secret: str) -> TokenAccesoSocio:
        credenciales = self._credenciales.obtener_por_client_id(client_id)
        if (
            credenciales is None
            or not credenciales.activo
            or not self._verificador(client_secret, credenciales)
        ):
            raise CredencialesIntegracionInvalidas(client_id)

        socio = self._socios.obtener(credenciales.socio_id)
        if (
            socio is None
            or socio.estado is not EstadoSocio.ACTIVO
            or socio.tenant_id != credenciales.tenant_id
        ):
            raise SocioIntegracionInactivo(credenciales.socio_id)

        scopes_vigentes = credenciales.scopes & socio.endpoints_autorizados
        if not scopes_vigentes:
            raise CredencialesIntegracionInvalidas(client_id)

        token, expires_in = self._generador_token(credenciales, scopes_vigentes)
        return TokenAccesoSocio(
            access_token=token,
            expires_in=expires_in,
            scope=" ".join(sorted(scope.value for scope in scopes_vigentes)),
        )
