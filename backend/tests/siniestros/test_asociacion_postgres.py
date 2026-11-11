"""Regresión: el asesor debe ver a su cliente aunque el UUID se guarde sin guiones.

En SQLite el UUID de `usuarios.id` se almacena sin guiones, mientras que `asesor_cliente`
lo guarda en forma canónica (con guiones). Un JOIN con cast de UUID fallaba en silencio y
el asesor no veía ningún cliente. Esta prueba fija el comportamiento correcto.
"""

import uuid
from datetime import date

import pytest
from pwdlib import PasswordHash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.identidad.asociacion import RepositorioAsesorClientePostgres
from app.identidad.asociacion_db import AsesorClienteDB
from app.identidad.modelos_db import UsuarioDB


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    UsuarioDB.__table__.create(engine)
    AsesorClienteDB.__table__.create(engine)
    fabrica = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with fabrica() as sesion:
        yield sesion
    engine.dispose()


def _crear_cliente(db, nombre="Ana", email="ana@gmail.com") -> UsuarioDB:
    usuario = UsuarioDB(
        id=uuid.uuid4(),
        nombre=nombre,
        apellido="Pérez",
        email=email,
        password_hash=PasswordHash.recommended().hash("Password123!"),
        rol="CLIENTE",
        activo=True,
        tipo_documento="CC",
        numero_documento=f"10{uuid.uuid4().int % 10**8:08d}",
        fecha_nacimiento=date(1999, 1, 1),
        kyc_validado=True,
        referencia_kyc="KYC-1",
        consentimiento_kyc=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def test_asesor_ve_cliente_pese_al_formato_del_uuid(db) -> None:
    asesor_id = str(uuid.uuid4())
    cliente = _crear_cliente(db)
    repo = RepositorioAsesorClientePostgres(db)

    # El id del cliente se asocia en forma canónica (con guiones).
    repo.asociar(asesor_id, str(cliente.id))

    clientes = repo.listar_clientes_de_asesor(asesor_id)

    assert len(clientes) == 1
    assert clientes[0].email == "ana@gmail.com"
    assert clientes[0].cliente_id == str(cliente.id)


def test_existe_asociacion_normaliza_guiones(db) -> None:
    asesor_id = str(uuid.uuid4())
    cliente = _crear_cliente(db)
    repo = RepositorioAsesorClientePostgres(db)
    repo.asociar(asesor_id, str(cliente.id))

    con_guiones = str(cliente.id)
    sin_guiones = con_guiones.replace("-", "")

    assert repo.existe_asociacion(asesor_id, con_guiones) is True
    # Aunque el token traiga el id sin guiones, debe reconocerse la asociación.
    assert repo.existe_asociacion(asesor_id, sin_guiones) is True


def test_asociar_es_idempotente_con_distintos_formatos(db) -> None:
    asesor_id = str(uuid.uuid4())
    cliente = _crear_cliente(db)
    repo = RepositorioAsesorClientePostgres(db)

    repo.asociar(asesor_id, str(cliente.id))
    repo.asociar(asesor_id, str(cliente.id).replace("-", ""))

    assert len(repo.listar_clientes_de_asesor(asesor_id)) == 1
