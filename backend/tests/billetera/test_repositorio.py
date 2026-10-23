from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.polizas.dominio.modelos import EnlaceCertificado, EstadoRegistroPoliza
from app.polizas.modelos_db import EnlaceCertificadoDB, PolizaDB
from app.polizas.repositorio import RepositorioEnlacesPostgres, RepositorioPolizasPostgres
from app.polizas.servicio import huella
from tests.billetera.fabrica import AHORA, poliza


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    PolizaDB.__table__.create(engine)
    EnlaceCertificadoDB.__table__.create(engine)
    with sessionmaker(bind=engine)() as sesion:
        yield sesion
    engine.dispose()


def test_guarda_y_recupera_la_poliza_completa(db):
    repositorio = RepositorioPolizasPostgres(db)
    original = poliza()

    repositorio.guardar(original)

    assert repositorio.obtener("POL-1") == original


def test_solo_devuelve_la_poliza_a_su_titular(db):
    repositorio = RepositorioPolizasPostgres(db)
    repositorio.guardar(poliza())

    assert repositorio.obtener_del_cliente("POL-1", "CLI-001") is not None
    assert repositorio.obtener_del_cliente("POL-1", "CLI-002") is None
    assert repositorio.obtener_del_cliente("NO-EXISTE", "CLI-001") is None


def test_lista_por_cliente(db):
    repositorio = RepositorioPolizasPostgres(db)
    repositorio.guardar(poliza())
    repositorio.guardar(poliza(poliza_id="POL-2", numero_poliza="SOL-VI-000002"))
    repositorio.guardar(
        poliza(poliza_id="POL-3", numero_poliza="SOL-VI-000003", cliente_id="CLI-002")
    )

    ids = sorted(p.poliza_id for p in repositorio.listar_por_cliente("CLI-001"))

    assert ids == ["POL-1", "POL-2"]


def test_actualiza_una_poliza_existente(db):
    repositorio = RepositorioPolizasPostgres(db)
    repositorio.guardar(poliza())

    repositorio.guardar(poliza(estado=EstadoRegistroPoliza.CANCELADA))

    assert repositorio.obtener("POL-1").estado is EstadoRegistroPoliza.CANCELADA


def test_guarda_y_recupera_el_enlace(db):
    RepositorioPolizasPostgres(db).guardar(poliza())
    repositorio = RepositorioEnlacesPostgres(db)
    enlace = EnlaceCertificado(
        huella_token=huella("abc"),
        poliza_id="POL-1",
        cliente_id="CLI-001",
        creado_en=AHORA,
        expira_en=AHORA + timedelta(hours=24),
    )

    repositorio.guardar(enlace)

    assert repositorio.obtener(huella("abc")) == enlace
    assert repositorio.obtener(huella("otro")) is None
