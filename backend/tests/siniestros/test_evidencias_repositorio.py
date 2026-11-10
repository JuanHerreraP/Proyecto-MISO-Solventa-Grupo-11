"""Evidencias, bitácora y registro idempotente sobre la base de datos (SQLite en memoria)."""

from datetime import timedelta

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.polizas.almacenamiento import AlmacenEnMemoria
from app.polizas.modelos_db import PolizaDB
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.siniestros.evidencias import DatosCaptura, EvidenciaDuplicada, ServicioEvidencias
from app.siniestros.modelos import SolicitudSiniestro, TipoSiniestro
from app.siniestros.modelos_db import AccesoEvidenciaDB, EvidenciaSiniestroDB, SiniestroDB
from app.siniestros.repositorio import ClaveIdempotenciaDuplicada, RepositorioSiniestrosPostgres
from app.siniestros.repositorio_evidencias import (
    RepositorioAuditoriaEvidenciasPostgres,
    RepositorioEvidenciasPostgres,
)
from app.siniestros.servicio import ServicioSiniestros
from tests.billetera.fabrica import poliza
from tests.siniestros.fabrica_evidencias import AHORA, CLIENTE, JPEG, MP4, OPERADOR, sha, siniestro


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for tabla in (PolizaDB, SiniestroDB, EvidenciaSiniestroDB, AccesoEvidenciaDB):
        tabla.__table__.create(engine)
    with sessionmaker(bind=engine)() as sesion:
        yield sesion
    engine.dispose()


def servicio(db, almacen=None, ahora=AHORA) -> ServicioEvidencias:
    return ServicioEvidencias(
        RepositorioSiniestrosPostgres(db),
        RepositorioEvidenciasPostgres(db),
        RepositorioAuditoriaEvidenciasPostgres(db),
        almacen or AlmacenEnMemoria(),
        reloj=lambda: ahora,
    )


def test_evidencia_y_bitacora_persisten(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    RepositorioSiniestrosPostgres(db).guardar(siniestro())
    almacen = AlmacenEnMemoria()
    datos = DatosCaptura(capturada_en=AHORA - timedelta(minutes=5), latitud=4.70, longitud=-74.14)

    cargada = servicio(db, almacen).adjuntar(CLIENTE, "SIN-1", JPEG, "image/jpeg", datos).evidencia
    db.expire_all()

    leida = RepositorioEvidenciasPostgres(db).obtener(cargada.evidencia_id)
    assert leida == cargada
    assert leida.capturada_en == AHORA - timedelta(minutes=5)
    assert leida.clave_almacenamiento == cargada.clave_almacenamiento
    _, contenido = servicio(db, almacen).leer(OPERADOR, "SIN-1", cargada.evidencia_id)
    assert contenido == JPEG

    bitacora = RepositorioAuditoriaEvidenciasPostgres(db).listar_por_siniestro("SIN-1")
    assert [(r.accion.value, r.actor_id) for r in bitacora] == [
        ("CARGA", "CLI-001"),
        ("DESCARGA", "OPS-1"),
    ]
    assert bitacora[0].ip == "10.0.0.5"
    assert bitacora[0].ocurrido_en == AHORA


def test_listado_en_orden_de_carga_y_conteo(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    RepositorioSiniestrosPostgres(db).guardar(siniestro())
    servicio(db).adjuntar(CLIENTE, "SIN-1", JPEG, "image/jpeg", DatosCaptura())
    despues = AHORA + timedelta(seconds=30)
    servicio(db, ahora=despues).adjuntar(CLIENTE, "SIN-1", MP4, "video/mp4", DatosCaptura())

    repositorio = RepositorioEvidenciasPostgres(db)
    assert repositorio.contar("SIN-1") == 2
    assert repositorio.contar("SIN-2") == 0
    assert [e.tipo.value for e in repositorio.listar_por_siniestro("SIN-1")] == ["FOTO", "VIDEO"]
    assert repositorio.obtener_por_huella("SIN-1", sha(MP4)).tipo.value == "VIDEO"


def test_la_base_impide_dos_evidencias_con_la_misma_huella(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    RepositorioSiniestrosPostgres(db).guardar(siniestro())
    cargada = servicio(db).adjuntar(CLIENTE, "SIN-1", JPEG, "image/jpeg", DatosCaptura()).evidencia

    copia = cargada.model_copy(update={"evidencia_id": "EVI-OTRA"})
    with pytest.raises(EvidenciaDuplicada):
        RepositorioEvidenciasPostgres(db).guardar(copia)
    assert RepositorioEvidenciasPostgres(db).contar("SIN-1") == 1


def test_registro_idempotente_persiste_tipo_y_clave(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    siniestros = ServicioSiniestros(
        RepositorioSiniestrosPostgres(db), RepositorioPolizasPostgres(db), reloj=lambda: AHORA
    )
    solicitud = SolicitudSiniestro(
        poliza_id="POL-1",
        tipo_siniestro=TipoSiniestro.DANO_MATERIAL,
        fecha_evento="2026-10-20",
        hora_evento="18:30:00",
        lugar="Aeropuerto El Dorado",
        descripcion="Se rompió la pantalla del celular.",
        estimacion_danos=850000,
    )

    primero = siniestros.registrar("CLI-001", "CLI-001", solicitud, "borrador-123")
    db.expire_all()
    repetido = siniestros.registrar("CLI-001", "CLI-001", solicitud, "borrador-123")

    assert primero.creado and not repetido.creado
    assert repetido.siniestro.siniestro_id == primero.siniestro.siniestro_id
    assert repetido.siniestro.tipo_siniestro is TipoSiniestro.DANO_MATERIAL
    filas = db.execute(text("SELECT tipo_siniestro, clave_idempotencia FROM siniestros")).all()
    assert filas == [("DANO_MATERIAL", "borrador-123")]
    # La clave no sale en la representación pública.
    assert "clave_idempotencia" not in repetido.siniestro.model_dump()


def test_la_base_impide_reusar_la_clave_del_mismo_cliente(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    repositorio = RepositorioSiniestrosPostgres(db)
    repositorio.guardar(siniestro(clave_idempotencia="borrador-1"))

    with pytest.raises(ClaveIdempotenciaDuplicada):
        repositorio.guardar(siniestro(siniestro_id="SIN-2", clave_idempotencia="borrador-1"))
    # Otro cliente puede usar la misma clave.
    repositorio.guardar(
        siniestro(siniestro_id="SIN-3", cliente_id="CLI-002", clave_idempotencia="borrador-1")
    )
    assert repositorio.obtener_por_clave("CLI-002", "borrador-1").siniestro_id == "SIN-3"


def test_la_migracion_agrega_las_columnas_de_hu04(monkeypatch) -> None:
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
            text(
                "CREATE TABLE siniestros (siniestro_id VARCHAR(50), cliente_id VARCHAR(50), "
                "evento_id VARCHAR(120))"
            )
        )
    monkeypatch.setattr(database, "engine", engine)

    database.preparar_esquema_registro()
    database.preparar_esquema_registro()  # Repetirla no falla.

    inspector = inspect(engine)
    columnas = {c["name"] for c in inspector.get_columns("siniestros")}
    assert {"tipo_siniestro", "clave_idempotencia"} <= columnas
    indices = {i["name"] for i in inspector.get_indexes("siniestros")}
    assert "uq_siniestros_cliente_clave" in indices
