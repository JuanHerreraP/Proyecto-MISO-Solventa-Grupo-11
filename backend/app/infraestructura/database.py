"""Configuración de base de datos."""

import logging
import os
import time

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

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


def esperar_base_disponible(intentos: int = 30, espera_segundos: float = 2.0) -> None:
    """Espera a que la base acepte conexiones antes de preparar el esquema.

    En RDS la instancia puede tardar en aceptar conexiones cuando la tarea ECS
    arranca. Reintentar evita que el contenedor muera y dispare el circuit
    breaker del servicio. Para SQLite el primer intento siempre tiene éxito.
    """
    for intento in range(1, intentos + 1):
        try:
            with engine.connect() as conexion:
                conexion.execute(text("SELECT 1"))
            if intento > 1:
                logger.info("Conexión a la base establecida tras %s intentos", intento)
            return
        except OperationalError as error:
            if intento == intentos:
                logger.error("No se pudo conectar a la base tras %s intentos", intentos)
                raise
            logger.warning(
                "Base no disponible (intento %s/%s): %s. Reintentando en %ss",
                intento,
                intentos,
                error.__class__.__name__,
                espera_segundos,
            )
            time.sleep(espera_segundos)


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
