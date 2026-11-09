import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.firmas.modelos import CanalOtp
from app.firmas.modelos_db import ProcesoFirmaDB
from app.firmas.repositorio import RepositorioFirmasPostgres, RepositorioTitularesPostgres
from app.identidad.modelos_db import UsuarioDB
from tests.firmas.fabrica import CLIENTE, COTIZACION, crear_entorno


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    ProcesoFirmaDB.__table__.create(engine)
    UsuarioDB.__table__.create(engine)
    with sessionmaker(bind=engine)() as sesion:
        yield sesion
    engine.dispose()


def proceso_firmado():
    e = crear_entorno()
    e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)
    huella = e.firmas.obtener_por_cotizacion(COTIZACION).huella_documento
    return e.servicio.firmar(CLIENTE, COTIZACION, e.ultimo_codigo, huella, "10.0.0.1", "ua")


def test_guarda_y_recupera_el_proceso_con_su_contrato_integro(db):
    repositorio = RepositorioFirmasPostgres(db)
    original = proceso_firmado()

    repositorio.guardar(original)
    db.expire_all()
    recuperado = repositorio.obtener_por_cotizacion(COTIZACION)

    assert recuperado == original
    assert recuperado.documento_integro()


def test_un_solo_proceso_por_cotizacion(db):
    repositorio = RepositorioFirmasPostgres(db)
    original = proceso_firmado()

    assert repositorio.crear(original) is True
    assert repositorio.crear(original.model_copy(update={"firma_id": "FIR-0002"})) is False


def test_lee_los_datos_del_titular_desde_identidad(db):
    usuario_id = uuid.uuid4()
    db.add(
        UsuarioDB(
            id=usuario_id,
            nombre="Laura",
            apellido="Gómez",
            email="laura@example.com",
            password_hash="x",
            rol="CLIENTE",
            activo=True,
            tipo_documento="CC",
            numero_documento="1020304050",
            celular="+573001234567",
            fecha_nacimiento=date(1990, 5, 1),
            kyc_validado=True,
            consentimiento_kyc=True,
        )
    )
    db.commit()
    titulares = RepositorioTitularesPostgres(db)

    titular = titulares.obtener(str(usuario_id))

    assert titular.nombre_completo == "Laura Gómez"
    assert titular.celular == "+573001234567"
    assert titulares.obtener(str(uuid.uuid4())) is None
    assert titulares.obtener("no-es-uuid") is None
