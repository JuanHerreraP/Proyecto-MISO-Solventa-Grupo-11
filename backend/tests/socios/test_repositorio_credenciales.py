from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.dominio.credenciales import generar_credenciales
from app.socios.dominio.modelos import EstadoSocio, SocioDistribucion
from app.socios.modelos_db import CredencialSocioDB, SocioDistribucionDB
from app.socios.repositorio import RepositorioSociosPostgres
from app.socios.repositorio_credenciales import RepositorioCredencialesSociosPostgres
from tests.socios.fabrica import solicitud_alta


def test_persiste_y_consulta_credenciales_por_client_id() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SocioDistribucionDB.__table__.create(engine)
    CredencialSocioDB.__table__.create(engine)
    fecha = datetime(2026, 10, 13, tzinfo=timezone.utc)
    socio = SocioDistribucion(
        **solicitud_alta().model_dump(),
        socio_id="SOCIO-001",
        tenant_id="TENANT-001",
        estado=EstadoSocio.ACTIVO,
        creado_en=fecha,
        actualizado_en=fecha,
    )
    credenciales, client_secret = generar_credenciales(
        socio_id=socio.socio_id,
        tenant_id=socio.tenant_id,
        scopes={CodigoEndpoint.COTIZACIONES_CREAR},
        creado_en=fecha,
    )

    with Session(engine) as db:
        RepositorioSociosPostgres(db).guardar(socio)
        repositorio = RepositorioCredencialesSociosPostgres(db)
        repositorio.guardar(credenciales)

        persistidas = repositorio.obtener_por_client_id(credenciales.client_id)
        credenciales_del_socio = repositorio.listar_por_socio(socio.socio_id)

    assert persistidas is not None
    assert persistidas.socio_id == socio.socio_id
    assert persistidas.tenant_id == socio.tenant_id
    assert persistidas.secret_hash != client_secret
    assert persistidas.scopes == {CodigoEndpoint.COTIZACIONES_CREAR}
    assert credenciales_del_socio == [persistidas]


def test_retorna_none_para_un_client_id_inexistente() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SocioDistribucionDB.__table__.create(engine)
    CredencialSocioDB.__table__.create(engine)

    with Session(engine) as db:
        repositorio = RepositorioCredencialesSociosPostgres(db)

        assert repositorio.obtener_por_client_id("client-inexistente") is None
