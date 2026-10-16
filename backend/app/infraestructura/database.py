"""Configuración de base de datos."""

import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./solventa.db"


class Base(DeclarativeBase):
    pass


engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    **engine_kwargs,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def preparar_esquema_registro() -> None:
    """Aplica los cambios aditivos requeridos por el registro en bases ya existentes."""
    inspector = inspect(engine)
    if inspector.has_table("sesiones_refresh"):
        columnas = {c["name"] for c in inspector.get_columns("sesiones_refresh")}
        if "ultima_actividad" not in columnas:
            with engine.begin() as conexion:
                conexion.execute(
                    text("ALTER TABLE sesiones_refresh ADD COLUMN ultima_actividad TIMESTAMP")
                )
                conexion.execute(
                    text("UPDATE sesiones_refresh SET ultima_actividad = fecha_emision")
                )
    if not inspector.has_table("usuarios"):
        return

    if "celular" not in {columna["name"] for columna in inspector.get_columns("usuarios")}:
        with engine.begin() as conexion:
            conexion.execute(text("ALTER TABLE usuarios ADD COLUMN celular VARCHAR(30)"))

    from app.identidad.modelos_db import UsuarioDB

    for indice in UsuarioDB.__table__.indexes:
        if indice.name == "uq_usuarios_tipo_documento_numero_documento":
            indice.create(bind=engine, checkfirst=True)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
