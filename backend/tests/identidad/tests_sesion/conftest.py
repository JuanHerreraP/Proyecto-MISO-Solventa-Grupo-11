"""Fixtures de HU02: llaves RSA temporales y base SQLite en memoria."""

import uuid
from datetime import date

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pwdlib import PasswordHash
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.identidad import tokens
from app.identidad.modelos_db import SesionRefreshDB, UsuarioDB

PASSWORD = "Password123!"


def _par_de_llaves() -> tuple[bytes, bytes]:
    llave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    privada = llave.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    publica = llave.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return privada, publica


@pytest.fixture(autouse=True)
def llaves_temporales(tmp_path, monkeypatch):
    """Las pruebas firman con llaves propias, no con las del repositorio."""

    privada, publica = _par_de_llaves()
    ruta_privada = tmp_path / "private_key.pem"
    ruta_publica = tmp_path / "public_key.pem"
    ruta_privada.write_bytes(privada)
    ruta_publica.write_bytes(publica)
    monkeypatch.setattr(tokens, "PRIVATE_KEY_PATH", ruta_privada)
    monkeypatch.setattr(tokens, "PUBLIC_KEY_PATH", ruta_publica)


@pytest.fixture
def fabrica_sesiones():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    UsuarioDB.__table__.create(engine)
    SesionRefreshDB.__table__.create(engine)
    yield sessionmaker(bind=engine, autoflush=False, autocommit=False)
    engine.dispose()


@pytest.fixture
def db(fabrica_sesiones):
    with fabrica_sesiones() as sesion:
        yield sesion


def crear_usuario(db: Session, email: str = "ana@gmail.com", activo: bool = True) -> UsuarioDB:
    usuario = UsuarioDB(
        id=uuid.uuid4(),
        nombre="Ana",
        apellido="Pérez",
        email=email,
        password_hash=PasswordHash.recommended().hash(PASSWORD),
        rol="CLIENTE",
        activo=activo,
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
