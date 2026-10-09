"""Configuración de base de datos."""

import os

from sqlalchemy import create_engine
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


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
