from datetime import datetime, timezone

from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.dominio.credenciales import CredencialesSocio
from app.socios.dominio.modelos import EstadoSocio, SocioDistribucion
from app.socios.repositorio import RepositorioSociosEnMemoria
from app.socios.repositorio_credenciales import RepositorioCredencialesSociosEnMemoria
from app.socios.servicio import SocioInactivo, SocioNoEncontrado
from app.socios.servicio_credenciales import ServicioCredencialesSocios
from tests.socios.fabrica import solicitud_alta

FECHA = datetime(2026, 10, 13, tzinfo=timezone.utc)


def crear_socio(estado: EstadoSocio = EstadoSocio.ACTIVO) -> SocioDistribucion:
    return SocioDistribucion(
        **solicitud_alta().model_dump(),
        socio_id="SOCIO-001",
        tenant_id="TENANT-001",
        estado=estado,
        creado_en=FECHA,
        actualizado_en=FECHA,
    )


def generar_credenciales_fijas(
    socio_id: str,
    tenant_id: str,
    scopes: set[CodigoEndpoint],
    creado_en: datetime,
) -> tuple[CredencialesSocio, str]:
    return (
        CredencialesSocio(
            socio_id=socio_id,
            tenant_id=tenant_id,
            client_id="solv_cliente_001",
            secret_hash="hash-seguro",
            scopes=scopes,
            creado_en=creado_en,
        ),
        "solv_secret_una_sola_vez",
    )


def test_aprovisiona_y_persiste_credenciales_del_socio_activo() -> None:
    socios = RepositorioSociosEnMemoria()
    credenciales = RepositorioCredencialesSociosEnMemoria()
    socio = crear_socio()
    socios.guardar(socio)
    servicio = ServicioCredencialesSocios(
        socios=socios,
        credenciales=credenciales,
        reloj=lambda: FECHA,
        generador=generar_credenciales_fijas,
    )

    emitidas = servicio.aprovisionar(socio.socio_id)
    persistidas = credenciales.obtener_por_client_id(emitidas.client_id)

    assert emitidas.client_id == "solv_cliente_001"
    assert emitidas.client_secret == "solv_secret_una_sola_vez"
    assert emitidas.socio_id == socio.socio_id
    assert emitidas.tenant_id == socio.tenant_id
    assert emitidas.scopes == socio.endpoints_autorizados
    assert persistidas is not None
    assert persistidas.secret_hash == "hash-seguro"
    assert not hasattr(persistidas, "client_secret")


def test_rechaza_aprovisionamiento_para_socio_inexistente() -> None:
    servicio = ServicioCredencialesSocios(
        socios=RepositorioSociosEnMemoria(),
        credenciales=RepositorioCredencialesSociosEnMemoria(),
    )

    error: Exception | None = None
    try:
        servicio.aprovisionar("SOCIO-INEXISTENTE")
    except Exception as capturada:  # noqa: BLE001 - se valida el tipo a continuación
        error = capturada

    assert isinstance(error, SocioNoEncontrado)


def test_rechaza_aprovisionamiento_para_socio_inactivo() -> None:
    socios = RepositorioSociosEnMemoria()
    socio = crear_socio(EstadoSocio.INACTIVO)
    socios.guardar(socio)
    servicio = ServicioCredencialesSocios(
        socios=socios,
        credenciales=RepositorioCredencialesSociosEnMemoria(),
    )

    error: Exception | None = None
    try:
        servicio.aprovisionar(socio.socio_id)
    except Exception as capturada:  # noqa: BLE001 - se valida el tipo a continuación
        error = capturada

    assert isinstance(error, SocioInactivo)
