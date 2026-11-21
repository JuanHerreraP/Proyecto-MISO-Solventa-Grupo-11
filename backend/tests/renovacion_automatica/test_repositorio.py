"""Preferencias, ciclos y pólizas por vencer sobre la base de datos (SQLite en memoria)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.polizas.dominio.modelos import EstadoRegistroPoliza
from app.polizas.dominio.renovacion_automatica import (
    EstadoCicloRenovacion,
    PreferenciaRenovacionAutomatica,
    nuevo_ciclo,
)
from app.polizas.modelos_db import (
    CicloRenovacionAutomaticaDB,
    PolizaDB,
    PreferenciaRenovacionAutomaticaDB,
)
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.polizas.repositorio_renovacion_automatica import (
    CicloConcurrente,
    RepositorioCiclosPostgres,
    RepositorioPreferenciasPostgres,
)
from tests.renovacion_automatica.fabrica import TARJETA, a_las_10
from tests.renovaciones.fabrica import AHORA, POLIZA, poliza


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for tabla in (PolizaDB, PreferenciaRenovacionAutomaticaDB, CicloRenovacionAutomaticaDB):
        tabla.__table__.create(engine)
    with sessionmaker(bind=engine)() as sesion:
        RepositorioPolizasPostgres(sesion).guardar(poliza())
        yield sesion
    engine.dispose()


def test_la_preferencia_guarda_el_token_y_lo_devuelve(db) -> None:
    repositorio = RepositorioPreferenciasPostgres(db)
    assert repositorio.obtener(POLIZA) is None

    repositorio.guardar(
        PreferenciaRenovacionAutomatica(
            poliza_id=POLIZA,
            activa=False,
            medio_pago=TARJETA,
            actualizado_por="CLI-001",
            actualizado_en=AHORA,
        )
    )
    leida = repositorio.obtener(POLIZA)
    assert leida.activa is False and leida.medio_pago == TARJETA
    assert leida.actualizado_en == AHORA

    repositorio.guardar(leida.model_copy(update={"activa": True, "medio_pago": None}))
    actualizada = repositorio.obtener(POLIZA)
    assert actualizada.activa is True and actualizada.medio_pago is None


def test_el_ciclo_es_unico_por_periodo_y_se_actualiza(db) -> None:
    repositorio = RepositorioCiclosPostgres(db)
    ciclo = nuevo_ciclo(poliza(), AHORA)
    repositorio.crear(ciclo)

    with pytest.raises(CicloConcurrente):
        repositorio.crear(ciclo)

    repositorio.guardar(
        ciclo.model_copy(
            update={
                "estado": EstadoCicloRenovacion.SIN_MEDIO_DE_PAGO,
                "renovacion_id": "REN-1",
                "prima_avisada": Decimal("420000.00"),
                "moneda": "COP",
                "preaviso_enviado_en": AHORA,
            }
        )
    )
    leido = repositorio.obtener(ciclo.ciclo_id)
    assert leido.estado is EstadoCicloRenovacion.SIN_MEDIO_DE_PAGO
    assert leido.prima_avisada == Decimal("420000.00")
    assert leido.preaviso_enviado_en == AHORA
    assert [c.ciclo_id for c in repositorio.por_poliza(POLIZA)] == [ciclo.ciclo_id]
    assert [c.ciclo_id for c in repositorio.abiertos()] == [ciclo.ciclo_id]

    repositorio.guardar(leido.model_copy(update={"estado": EstadoCicloRenovacion.NO_PAGADA}))
    assert repositorio.abiertos() == []


def test_un_ciclo_renovado_sigue_abierto_hasta_enviar_el_contrato(db) -> None:
    repositorio = RepositorioCiclosPostgres(db)
    ciclo = nuevo_ciclo(poliza(), AHORA).model_copy(
        update={"estado": EstadoCicloRenovacion.RENOVADA, "renovacion_id": "REN-1"}
    )
    repositorio.crear(ciclo)
    assert len(repositorio.abiertos()) == 1

    repositorio.guardar(
        ciclo.model_copy(
            update={
                "huella_documento": "a" * 64,
                "clave_documento": "renovaciones/x.pdf",
                "tamano_documento": 10,
                "contrato_enviado_en": a_las_10(date(2026, 12, 31)),
            }
        )
    )
    assert repositorio.abiertos() == []


def test_polizas_por_vencer_en_el_rango_y_sin_canceladas(db) -> None:
    repositorio = RepositorioPolizasPostgres(db)
    repositorio.guardar(
        poliza(poliza_id="POL-2", numero_poliza="SOL-2", fecha_fin=date(2027, 3, 1))
    )
    repositorio.guardar(
        poliza(
            poliza_id="POL-3",
            numero_poliza="SOL-3",
            estado=EstadoRegistroPoliza.CANCELADA,
            cancelada_en=AHORA - timedelta(days=1),
        )
    )

    por_vencer = repositorio.listar_por_vencer(date(2026, 12, 1), date(2026, 12, 31))

    assert [p.poliza_id for p in por_vencer] == [POLIZA]
