"""Cancelaciones, pólizas y siniestros sobre la base de datos (SQLite en memoria)."""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cotizaciones.repositorio import RepositorioCotizacionesEnMemoria
from app.desembolsos.modelos_db import DesembolsoDB
from app.desembolsos.repositorio import RepositorioDesembolsosPostgres
from app.polizas.cancelacion import ServicioCancelaciones
from app.polizas.dominio.cancelacion import CancelacionNoPermitida
from app.polizas.dominio.modelos import EstadoRegistroPoliza
from app.polizas.modelos_db import CancelacionDB, PolizaDB
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.polizas.repositorio_cancelaciones import (
    CancelacionConcurrente,
    RepositorioCancelacionesPostgres,
)
from app.siniestros.modelos import EstadoSiniestro
from app.siniestros.modelos_db import SiniestroDB
from app.siniestros.repositorio import RepositorioSiniestrosPostgres
from tests.cancelaciones.fabrica import (
    AHORA,
    POLIZA,
    TITULAR,
    Reloj,
    cotizacion,
    poliza,
    siniestro,
    solicitud,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for tabla in (PolizaDB, CancelacionDB, SiniestroDB, DesembolsoDB):
        tabla.__table__.create(engine)
    with sessionmaker(bind=engine)() as sesion:
        yield sesion
    engine.dispose()


def servicio(db) -> ServicioCancelaciones:
    cotizaciones = RepositorioCotizacionesEnMemoria()
    cotizaciones.guardar(cotizacion())
    return ServicioCancelaciones(
        RepositorioPolizasPostgres(db),
        RepositorioCancelacionesPostgres(db),
        RepositorioSiniestrosPostgres(db),
        RepositorioDesembolsosPostgres(db),
        cotizaciones,
        reloj=Reloj(),
    )


def test_cancelar_guarda_la_cancelacion_y_la_poliza_en_una_transaccion(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())

    cancelacion, creada = servicio(db).confirmar(
        TITULAR, POLIZA, solicitud(), clave_idempotencia="k-1"
    )

    assert creada is True
    db.expire_all()
    guardada = RepositorioPolizasPostgres(db).obtener(POLIZA)
    assert guardada.estado is EstadoRegistroPoliza.CANCELADA
    assert guardada.cancelada_en == AHORA
    leida = RepositorioCancelacionesPostgres(db).por_poliza(POLIZA)
    assert leida == cancelacion
    assert leida.saldo_estimado == Decimal("74794.52")
    assert RepositorioCancelacionesPostgres(db).por_clave(POLIZA, "k-1") == cancelacion
    assert RepositorioCancelacionesPostgres(db).por_clave(POLIZA, "otra") is None


def test_repetir_la_clave_devuelve_la_cancelacion_guardada(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    primera, _ = servicio(db).confirmar(TITULAR, POLIZA, solicitud(), clave_idempotencia="k-1")

    segunda, creada = servicio(db).confirmar(TITULAR, POLIZA, solicitud(), clave_idempotencia="k-1")

    assert creada is False
    assert segunda == primera


def test_una_poliza_solo_se_cancela_una_vez_a_nivel_de_base_de_datos(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    cancelacion, _ = servicio(db).confirmar(TITULAR, POLIZA, solicitud())
    cancelaciones = RepositorioCancelacionesPostgres(db)

    with pytest.raises(CancelacionConcurrente):
        cancelaciones.registrar(
            cancelacion, poliza(estado=EstadoRegistroPoliza.CANCELADA, cancelada_en=AHORA)
        )

    # El intento fallido no deja la sesión inutilizable ni cambia lo guardado.
    assert cancelaciones.por_poliza(POLIZA) == cancelacion


def test_los_siniestros_en_tramite_bloquean_con_datos_reales(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    RepositorioSiniestrosPostgres(db).guardar(siniestro(EstadoSiniestro.EN_EVALUACION))

    with pytest.raises(CancelacionNoPermitida):
        servicio(db).confirmar(TITULAR, POLIZA, solicitud())

    db.expire_all()
    assert RepositorioPolizasPostgres(db).obtener(POLIZA).estado is EstadoRegistroPoliza.VIGENTE
    assert RepositorioCancelacionesPostgres(db).por_poliza(POLIZA) is None


def test_listar_siniestros_por_poliza_filtra_y_ordena_del_mas_reciente(db) -> None:
    repo = RepositorioSiniestrosPostgres(db)
    repo.guardar(siniestro(EstadoSiniestro.REGISTRADO, "SIN-1"))
    repo.guardar(siniestro(EstadoSiniestro.RECHAZADO, "SIN-2"))
    otro = siniestro(EstadoSiniestro.REGISTRADO, "SIN-3").model_copy(
        update={"poliza_id": "POL-OTRA"}
    )
    repo.guardar(otro)

    ids = {s.siniestro_id for s in repo.listar_por_poliza(POLIZA)}

    assert ids == {"SIN-1", "SIN-2"}
    assert repo.listar_por_poliza("POL-NINGUNA") == []
