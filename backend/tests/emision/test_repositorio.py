"""La emisión sobre los repositorios de base de datos (SQLite en memoria)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.firmas.modelos_db import ProcesoFirmaDB
from app.firmas.repositorio import RepositorioFirmasPostgres
from app.polizas.emision import ServicioEmision, poliza_id_de
from app.polizas.modelos_db import DocumentoPolizaDB, PolizaDB
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.polizas.repositorio_documentos import (
    DocumentoPoliza,
    RepositorioDocumentosPostgres,
)
from tests.emision.fabrica import crear_entorno
from tests.firmas.fabrica import AHORA, CLIENTE, COTIZACION

POLIZA = poliza_id_de(COTIZACION)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for tabla in (ProcesoFirmaDB, PolizaDB, DocumentoPolizaDB):
        tabla.__table__.create(engine)
    with sessionmaker(bind=engine)() as sesion:
        yield sesion
    engine.dispose()


def emision_en_base_de_datos(db):
    """Firma en memoria y emite con los repositorios reales de póliza, documento y firma."""
    memoria = crear_entorno()
    firmado = memoria.firmar()
    firmas = RepositorioFirmasPostgres(db)
    assert firmas.crear(firmado)
    servicio = ServicioEmision(
        polizas=RepositorioPolizasPostgres(db),
        documentos=RepositorioDocumentosPostgres(db),
        firmas=firmas,
        cotizaciones=memoria.cotizaciones,
        almacen=memoria.almacen,
        correo=memoria.comunicaciones,
        notificador=memoria.comunicaciones,
        reloj=memoria.reloj,
    )
    return servicio, memoria


def test_emite_y_persiste_la_poliza_y_su_documento(db) -> None:
    servicio, memoria = emision_en_base_de_datos(db)

    emitida = servicio.emitir(COTIZACION)

    guardada = RepositorioPolizasPostgres(db).obtener_del_cliente(POLIZA, CLIENTE)
    assert guardada == emitida
    assert str(guardada.prima_total) == "94500.00"
    documento = RepositorioDocumentosPostgres(db).obtener(POLIZA)
    assert documento.clave_almacenamiento == f"polizas/{POLIZA}.pdf"
    assert memoria.almacen.leer(documento.clave_almacenamiento).startswith(b"%PDF")
    assert servicio.poliza_emitida(COTIZACION) == POLIZA


def test_repetir_la_emision_no_duplica_filas_ni_cambia_el_documento(db) -> None:
    servicio, _ = emision_en_base_de_datos(db)
    primera = servicio.emitir(COTIZACION)
    huella = RepositorioDocumentosPostgres(db).obtener(POLIZA).huella_sha256

    segunda = servicio.emitir(COTIZACION)

    assert segunda == primera
    assert db.query(PolizaDB).count() == 1
    assert db.query(DocumentoPolizaDB).count() == 1
    assert RepositorioDocumentosPostgres(db).obtener(POLIZA).huella_sha256 == huella


def test_las_marcas_de_entrega_se_conservan_entre_sesiones(db) -> None:
    servicio, memoria = emision_en_base_de_datos(db)
    servicio.emitir(COTIZACION)

    servicio.notificar(POLIZA)
    servicio.notificar(POLIZA)

    documento = RepositorioDocumentosPostgres(db).obtener(POLIZA)
    assert documento.bienvenida_enviada_en is not None
    assert documento.notificada_en is not None
    assert documento.bienvenida_enviada_en.tzinfo is not None
    assert len(memoria.comunicaciones.correos) == 1


def test_un_documento_inexistente_devuelve_none_y_guardar_actualiza(db) -> None:
    repositorio = RepositorioDocumentosPostgres(db)
    assert repositorio.obtener("POL-NADA") is None

    documento = DocumentoPoliza(
        poliza_id="POL-1",
        clave_almacenamiento="polizas/POL-1.pdf",
        huella_sha256="a" * 64,
        tamano_bytes=10,
        creado_en=AHORA,
    )
    # La tabla exige una póliza existente en bases con claves foráneas activas; SQLite no.
    repositorio.guardar(documento)
    repositorio.guardar(documento.model_copy(update={"notificada_en": AHORA}))

    assert db.query(DocumentoPolizaDB).count() == 1
    assert repositorio.obtener("POL-1").notificada_en == AHORA
