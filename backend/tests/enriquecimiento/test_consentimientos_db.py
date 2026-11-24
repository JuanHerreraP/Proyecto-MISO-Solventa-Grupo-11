from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.infraestructura.database import Base
from app.perfilamiento.enriquecimiento.consentimientos_db import (
    RepositorioConsentimientosPostgres,
)
from app.perfilamiento.enriquecimiento.modelos import Consentimiento

AHORA = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def fabrica():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False)


def consentimiento(cliente="CLI-001", dias=30, id_="CONS-001"):
    return Consentimiento(
        consentimiento_id=id_, cliente_id=cliente, vence_en=AHORA + timedelta(days=dias)
    )


def test_lo_registrado_por_una_replica_lo_ve_otra(fabrica):
    una = RepositorioConsentimientosPostgres(fabrica)
    otra = RepositorioConsentimientosPostgres(fabrica)

    una.registrar(consentimiento())

    assert otra.vigente("CLI-001", AHORA) == consentimiento()


def test_vencido_o_inexistente_no_es_vigente(fabrica):
    repo = RepositorioConsentimientosPostgres(fabrica)
    repo.registrar(consentimiento(dias=1))

    assert repo.vigente("CLI-001", AHORA + timedelta(days=1)) is None
    assert repo.vigente("OTRO", AHORA) is None


def test_registrar_de_nuevo_reemplaza_el_consentimiento(fabrica):
    repo = RepositorioConsentimientosPostgres(fabrica)
    repo.registrar(consentimiento(id_="CONS-001"))
    repo.registrar(consentimiento(id_="CONS-002", dias=60))

    vigente = repo.vigente("CLI-001", AHORA)
    assert vigente.consentimiento_id == "CONS-002"
