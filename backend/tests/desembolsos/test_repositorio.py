"""Desembolsos y cuentas sobre la base de datos (SQLite en memoria)."""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.desembolsos.modelos_db import CuentaDesembolsoDB, DesembolsoDB
from app.desembolsos.red_simulada import RedDesembolsosSimulada
from app.desembolsos.repositorio import RepositorioCuentasPostgres, RepositorioDesembolsosPostgres
from app.desembolsos.servicio import ServicioDesembolsos
from app.polizas.modelos_db import PolizaDB
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.siniestros.evaluacion import ServicioEvaluacion
from app.siniestros.modelos import EstadoSiniestro
from app.siniestros.modelos_db import SiniestroDB
from app.siniestros.repositorio import RepositorioSiniestrosPostgres
from tests.billetera.fabrica import poliza
from tests.desembolsos.fabrica import AHORA, CLIENTE, OPERADOR, cuenta, siniestro


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for tabla in (PolizaDB, SiniestroDB, DesembolsoDB, CuentaDesembolsoDB):
        tabla.__table__.create(engine)
    with sessionmaker(bind=engine)() as sesion:
        yield sesion
    engine.dispose()


def servicios(db):
    desembolsos = ServicioDesembolsos(
        RepositorioDesembolsosPostgres(db),
        RepositorioCuentasPostgres(db),
        RedDesembolsosSimulada(),
        reloj=lambda: AHORA,
    )
    evaluacion = ServicioEvaluacion(
        RepositorioSiniestrosPostgres(db),
        RepositorioPolizasPostgres(db),
        desembolsos,
        reloj=lambda: AHORA,
    )
    return desembolsos, evaluacion


def test_aprobar_y_desembolsar_persisten(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    RepositorioSiniestrosPostgres(db).guardar(siniestro())
    desembolsos, evaluacion = servicios(db)
    desembolsos.registrar_cuenta(CLIENTE, cuenta())

    _, desembolso = evaluacion.aprobar("SIN-1", OPERADOR)
    db.expire_all()

    leido = RepositorioSiniestrosPostgres(db).obtener("SIN-1")
    assert leido.estado is EstadoSiniestro.APROBADO
    assert leido.monto_aprobado == Decimal("850000.00")
    assert leido.evaluado_en == AHORA
    assert RepositorioDesembolsosPostgres(db).obtener_por_siniestro("SIN-1") == desembolso
    assert RepositorioCuentasPostgres(db).obtener(CLIENTE).ultimos_digitos == "5678"
    assert [s.siniestro_id for s in RepositorioSiniestrosPostgres(db).listar()] == ["SIN-1"]


def test_la_base_impide_dos_desembolsos_del_mismo_siniestro(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    RepositorioSiniestrosPostgres(db).guardar(siniestro())
    _, evaluacion = servicios(db)
    _, primero = evaluacion.aprobar("SIN-1", OPERADOR)

    duplicado = primero.model_copy(update={"desembolso_id": "DES-OTRO"})

    assert RepositorioDesembolsosPostgres(db).crear(duplicado) is False
    assert RepositorioDesembolsosPostgres(db).obtener_por_siniestro("SIN-1") == primero


def test_la_cuenta_no_guarda_el_numero_completo(db) -> None:
    desembolsos, _ = servicios(db)
    desembolsos.registrar_cuenta(CLIENTE, cuenta("4567891234"))

    fila = db.execute(text("SELECT * FROM cuentas_desembolso")).mappings().one()

    assert "4567891234" not in " ".join(str(v) for v in fila.values())


def test_la_migracion_agrega_las_columnas_de_evaluacion(monkeypatch) -> None:
    from app.infraestructura import database

    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    with engine.begin() as conexion:
        conexion.execute(
            text(
                "CREATE TABLE usuarios (id VARCHAR(36), celular VARCHAR(30), "
                "tipo_documento VARCHAR(20), numero_documento VARCHAR(50))"
            )
        )
        conexion.execute(
            text("CREATE TABLE siniestros (siniestro_id VARCHAR(50), evento_id VARCHAR(120))")
        )
    monkeypatch.setattr(database, "engine", engine)

    database.preparar_esquema_registro()
    database.preparar_esquema_registro()  # Repetirla no falla.

    columnas = {c["name"] for c in inspect(engine).get_columns("siniestros")}
    assert {"monto_aprobado", "evaluado_por", "evaluado_en", "motivo_rechazo"} <= columnas
