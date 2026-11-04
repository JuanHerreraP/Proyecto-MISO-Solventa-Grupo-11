"""Endosos y pólizas sobre la base de datos (SQLite en memoria)."""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cotizaciones.repositorio import RepositorioCotizacionesEnMemoria
from app.identidad.modelos import Rol
from app.polizas.almacenamiento import AlmacenEnMemoria
from app.polizas.dominio.endosos import SolicitudModificacion
from app.polizas.endosos import ServicioEndosos, Solicitante
from app.polizas.modelos_db import EndosoDB, PolizaDB
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.polizas.repositorio_endosos import EndosoConcurrente, RepositorioEndososPostgres
from tests.endosos.fabrica import (
    CLIENTE,
    POLIZA,
    Reloj,
    cotizacion,
    dos_beneficiarios,
    poliza,
    solo_coberturas,
)

TITULAR = Solicitante(CLIENTE, Rol.CLIENTE)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for tabla in (PolizaDB, EndosoDB):
        tabla.__table__.create(engine)
    with sessionmaker(bind=engine)() as sesion:
        yield sesion
    engine.dispose()


def servicio(db) -> ServicioEndosos:
    cotizaciones = RepositorioCotizacionesEnMemoria()
    cotizaciones.guardar(cotizacion())
    return ServicioEndosos(
        RepositorioPolizasPostgres(db),
        RepositorioEndososPostgres(db),
        cotizaciones,
        AlmacenEnMemoria(),
        reloj=Reloj(),
    )


def test_la_poliza_guarda_coberturas_opcionales_y_beneficiarios(db) -> None:
    polizas = RepositorioPolizasPostgres(db)
    polizas.guardar(poliza(beneficiarios=dos_beneficiarios()))

    leida = polizas.obtener(POLIZA)

    assert [b.porcentaje for b in leida.beneficiarios] == [Decimal("60"), Decimal("40")]
    assert leida.coberturas_opcionales == []


def test_una_poliza_anterior_a_hu16_se_lee_sin_opcionales(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    db.execute(text("UPDATE polizas SET coberturas_opcionales = NULL, beneficiarios = NULL"))
    db.commit()
    db.expire_all()

    leida = RepositorioPolizasPostgres(db).obtener(POLIZA)

    assert leida.coberturas_opcionales == [] and leida.beneficiarios == []


def test_confirmar_guarda_endoso_y_poliza_juntos(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    s = servicio(db)

    endoso, _ = s.confirmar(
        TITULAR,
        POLIZA,
        SolicitudModificacion(
            beneficiarios=dos_beneficiarios(),
            coberturas_opcionales=solo_coberturas(
                INCAPACIDAD_TOTAL_PERMANENTE="50000000"
            ).coberturas_opcionales,
        ),
        "clave-1",
    )
    db.expire_all()

    leido = RepositorioEndososPostgres(db).obtener(POLIZA, endoso.endoso_id)
    assert leido == endoso
    assert RepositorioEndososPostgres(db).por_clave(POLIZA, "clave-1") == endoso
    actualizada = RepositorioPolizasPostgres(db).obtener(POLIZA)
    assert actualizada.prima_total == Decimal("186600.00")
    assert len(actualizada.beneficiarios) == 2
    assert actualizada.coberturas_opcionales[0].codigo == "INCAPACIDAD_TOTAL_PERMANENTE"


def test_el_numero_repetido_revierte_todo(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    s = servicio(db)
    primero, _ = s.confirmar(TITULAR, POLIZA, solo_coberturas(AUXILIO_FUNERARIO="5000000"))
    repositorio = RepositorioEndososPostgres(db)
    duplicado = primero.model_copy(update={"endoso_id": "END-OTRO"})
    cambiada = poliza(prima_total=Decimal("999999.00"))

    with pytest.raises(EndosoConcurrente):
        repositorio.registrar(duplicado, cambiada)

    assert RepositorioPolizasPostgres(db).obtener(POLIZA).prima_total == primero.prima_nueva
    assert len(repositorio.listar_por_poliza(POLIZA)) == 1


def test_la_migracion_agrega_las_columnas_a_una_tabla_existente(monkeypatch) -> None:
    from app.infraestructura import database

    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    with engine.begin() as conexion:
        conexion.execute(text("CREATE TABLE polizas (poliza_id VARCHAR(50) PRIMARY KEY)"))
    monkeypatch.setattr(database, "engine", engine)

    database._agregar_columnas_endosos(inspect(engine))
    database._agregar_columnas_endosos(inspect(engine))  # Repetirla no falla.

    columnas = {c["name"] for c in inspect(engine).get_columns("polizas")}
    assert {"coberturas_opcionales", "beneficiarios"} <= columnas
