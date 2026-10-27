"""Persistencia de siniestros contra SQLite en memoria (HU20).

Cubre `RepositorioSiniestrosPostgres` y los mapeos `_a_persistencia`/`_a_dominio`/`_con_zona`.
"""

from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.polizas.modelos_db import PolizaDB
from app.siniestros.modelos import EstadoSiniestro, OrigenSiniestro, Siniestro
from app.siniestros.modelos_db import SiniestroDB
from app.siniestros.repositorio import (
    RepositorioSiniestrosEnMemoria,
    RepositorioSiniestrosPostgres,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # La tabla de siniestros tiene FK a polizas; se crea también para que el esquema sea válido.
    PolizaDB.__table__.create(engine)
    SiniestroDB.__table__.create(engine)
    with sessionmaker(bind=engine)() as sesion:
        yield sesion
    engine.dispose()


def siniestro(
    siniestro_id: str = "SIN-1",
    cliente_id: str = "CLI-001",
    poliza_id: str = "POL-1",
    origen: OrigenSiniestro = OrigenSiniestro.MANUAL,
    evento_id: str | None = None,
    registrado_en: datetime = datetime(2026, 10, 21, 15, 0, tzinfo=UTC),
) -> Siniestro:
    return Siniestro(
        siniestro_id=siniestro_id,
        cliente_id=cliente_id,
        poliza_id=poliza_id,
        origen=origen,
        estado=EstadoSiniestro.REGISTRADO,
        evento_id=evento_id,
        fecha_evento=date(2026, 10, 20),
        hora_evento=time(18, 30),
        lugar="Aeropuerto El Dorado",
        descripcion="El vuelo fue cancelado y hubo gastos adicionales.",
        estimacion_danos=Decimal("850000.00"),
        moneda="COP",
        registrado_por=cliente_id,
        registrado_en=registrado_en,
    )


def test_guarda_y_recupera_el_siniestro_completo(db):
    repositorio = RepositorioSiniestrosPostgres(db)
    original = siniestro(evento_id="EVT-1")

    repositorio.guardar(original)

    recuperado = repositorio.obtener("SIN-1")
    assert recuperado == original
    assert recuperado.origen is OrigenSiniestro.MANUAL
    assert recuperado.evento_id == "EVT-1"


def test_obtener_inexistente_devuelve_none(db):
    assert RepositorioSiniestrosPostgres(db).obtener("NO-EXISTE") is None


def test_actualiza_un_siniestro_existente(db):
    repositorio = RepositorioSiniestrosPostgres(db)
    repositorio.guardar(siniestro())

    # Mismo id: debe actualizar en vez de insertar otro.
    repositorio.guardar(siniestro(origen=OrigenSiniestro.AUTOMATICO, evento_id="EVT-9"))

    recuperado = repositorio.obtener("SIN-1")
    assert recuperado.origen is OrigenSiniestro.AUTOMATICO
    assert recuperado.evento_id == "EVT-9"
    assert len(repositorio.listar_por_cliente("CLI-001")) == 1


def test_obtener_por_evento(db):
    repositorio = RepositorioSiniestrosPostgres(db)
    repositorio.guardar(siniestro(evento_id="EVT-1"))

    assert repositorio.obtener_por_evento("EVT-1").siniestro_id == "SIN-1"
    assert repositorio.obtener_por_evento("OTRO") is None


def test_listar_por_cliente_ordena_del_mas_reciente_al_mas_antiguo(db):
    repositorio = RepositorioSiniestrosPostgres(db)
    repositorio.guardar(
        siniestro(siniestro_id="SIN-VIEJO", registrado_en=datetime(2026, 1, 1, tzinfo=UTC))
    )
    repositorio.guardar(
        siniestro(siniestro_id="SIN-NUEVO", registrado_en=datetime(2026, 10, 1, tzinfo=UTC))
    )
    repositorio.guardar(siniestro(siniestro_id="SIN-OTRO", cliente_id="CLI-002"))

    ids = [s.siniestro_id for s in repositorio.listar_por_cliente("CLI-001")]

    assert ids == ["SIN-NUEVO", "SIN-VIEJO"]


def test_las_fechas_sin_zona_se_normalizan_a_utc(db):
    repositorio = RepositorioSiniestrosPostgres(db)
    repositorio.guardar(siniestro())

    # SQLite devuelve la fecha sin tzinfo; el repositorio la marca como UTC al mapear a dominio.
    recuperado = repositorio.obtener("SIN-1")
    assert recuperado.registrado_en.tzinfo is not None
    assert recuperado.registrado_en == datetime(2026, 10, 21, 15, 0, tzinfo=UTC)


def test_en_memoria_obtener_por_evento_recorre_sin_coincidencia():
    # Repo en memoria: hay siniestros pero ninguno con ese evento_id -> recorre y devuelve None.
    repositorio = RepositorioSiniestrosEnMemoria()
    repositorio.guardar(siniestro(siniestro_id="SIN-1", evento_id="EVT-1"))
    repositorio.guardar(siniestro(siniestro_id="SIN-2", evento_id=None))

    assert repositorio.obtener_por_evento("NO-EXISTE") is None
    assert repositorio.obtener_por_evento("EVT-1").siniestro_id == "SIN-1"
