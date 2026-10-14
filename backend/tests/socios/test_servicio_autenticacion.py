from datetime import datetime, timezone

from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.dominio.credenciales import CredencialesSocio
from app.socios.dominio.modelos import EstadoSocio, SocioDistribucion
from app.socios.repositorio import RepositorioSociosEnMemoria
from app.socios.repositorio_credenciales import RepositorioCredencialesSociosEnMemoria
from app.socios.servicio_autenticacion import (
    CredencialesIntegracionInvalidas,
    ServicioAutenticacionSocios,
    SocioIntegracionInactivo,
)
from tests.socios.fabrica import solicitud_alta

FECHA = datetime(2026, 10, 13, tzinfo=timezone.utc)


def preparar_servicio(
    estado_socio: EstadoSocio = EstadoSocio.ACTIVO,
    secreto_valido: bool = True,
) -> ServicioAutenticacionSocios:
    socios = RepositorioSociosEnMemoria()
    credenciales = RepositorioCredencialesSociosEnMemoria()
    socio = SocioDistribucion(
        **solicitud_alta().model_dump(),
        socio_id="SOCIO-001",
        tenant_id="TENANT-001",
        estado=estado_socio,
        creado_en=FECHA,
        actualizado_en=FECHA,
    )
    socios.guardar(socio)
    credenciales.guardar(
        CredencialesSocio(
            socio_id=socio.socio_id,
            tenant_id=socio.tenant_id,
            client_id="solv_cliente_001",
            secret_hash="hash-seguro",
            scopes={CodigoEndpoint.COTIZACIONES_CREAR},
            creado_en=FECHA,
        )
    )
    return ServicioAutenticacionSocios(
        socios=socios,
        credenciales=credenciales,
        verificador=lambda _secret, _credenciales: secreto_valido,
        generador_token=lambda _credenciales, _scopes: ("jwt-socio", 900),
    )


def capturar_error(accion) -> Exception | None:
    try:
        accion()
    except Exception as error:  # noqa: BLE001 - la prueba valida el tipo concreto
        return error
    return None


def test_intercambia_credenciales_validas_por_token() -> None:
    resultado = preparar_servicio().autenticar(
        "solv_cliente_001",
        "solv_secret_correcto",
    )

    assert resultado.access_token == "jwt-socio"
    assert resultado.token_type == "bearer"
    assert resultado.expires_in == 900
    assert resultado.scope == "cotizaciones:crear"


def test_rechaza_un_secreto_incorrecto() -> None:
    servicio = preparar_servicio(secreto_valido=False)

    error = capturar_error(
        lambda: servicio.autenticar("solv_cliente_001", "secreto-incorrecto")
    )

    assert isinstance(error, CredencialesIntegracionInvalidas)


def test_rechaza_credenciales_de_un_socio_inactivo() -> None:
    servicio = preparar_servicio(estado_socio=EstadoSocio.INACTIVO)

    error = capturar_error(
        lambda: servicio.autenticar("solv_cliente_001", "solv_secret_correcto")
    )

    assert isinstance(error, SocioIntegracionInactivo)
