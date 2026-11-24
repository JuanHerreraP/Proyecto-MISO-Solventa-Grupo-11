"""Registro de eventos ya procesados por cada consumidor (consumidor idempotente).

Antes de realizar una operación financiera, el consumidor pregunta si ese evento ya se procesó.
Es la primera barrera; la segunda es la restricción única de la propia operación (un solo
desembolso por siniestro), que protege aun si dos consumidores leen el mismo evento a la vez.
"""

from datetime import datetime
from typing import Protocol

from sqlalchemy import DateTime, String
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.infraestructura.database import Base


class EventoProcesadoDB(Base):
    __tablename__ = "eventos_procesados"

    evento_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    consumidor: Mapped[str] = mapped_column(String(50), primary_key=True)
    procesado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RepositorioEventosProcesados(Protocol):
    def ya_procesado(self, evento_id: str, consumidor: str) -> bool: ...

    def marcar(self, evento_id: str, consumidor: str, ahora: datetime) -> bool:
        """Registra el evento. Devuelve False si ese consumidor ya lo había registrado."""
        ...


class RepositorioEventosProcesadosEnMemoria:
    def __init__(self):
        self._vistos: set[tuple[str, str]] = set()

    def ya_procesado(self, evento_id: str, consumidor: str) -> bool:
        return (evento_id, consumidor) in self._vistos

    def marcar(self, evento_id: str, consumidor: str, ahora: datetime) -> bool:
        clave = (evento_id, consumidor)
        if clave in self._vistos:
            return False
        self._vistos.add(clave)
        return True


class RepositorioEventosProcesadosPostgres:
    def __init__(self, db: Session):
        self._db = db

    def ya_procesado(self, evento_id: str, consumidor: str) -> bool:
        return self._db.get(EventoProcesadoDB, (evento_id, consumidor)) is not None

    def marcar(self, evento_id: str, consumidor: str, ahora: datetime) -> bool:
        self._db.add(
            EventoProcesadoDB(evento_id=evento_id, consumidor=consumidor, procesado_en=ahora)
        )
        try:
            self._db.commit()
        except IntegrityError:
            # Otro consumidor lo registró entre la consulta y la inserción: ya está procesado.
            self._db.rollback()
            return False
        return True
