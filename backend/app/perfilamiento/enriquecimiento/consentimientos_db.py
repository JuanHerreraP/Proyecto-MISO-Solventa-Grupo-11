"""Consentimientos en base de datos, para que todas las réplicas del backend los vean.

Con la memoria del proceso, un consentimiento registrado en una réplica no existiría en la otra
y el enriquecimiento fallaría de forma intermitente. Cada operación abre su propia sesión: el
repositorio vive en un singleton del proceso y no puede compartir una sesión entre solicitudes.
"""

from collections.abc import Callable
from contextlib import closing
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.infraestructura.database import Base, SessionLocal
from app.perfilamiento.enriquecimiento.modelos import Consentimiento


class ConsentimientoDB(Base):
    __tablename__ = "consentimientos"

    cliente_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    consentimiento_id: Mapped[str] = mapped_column(String(120), nullable=False)
    vence_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RepositorioConsentimientosPostgres:
    def __init__(self, fabrica_sesion: Callable[[], Session] = SessionLocal):
        self._fabrica_sesion = fabrica_sesion

    def registrar(self, consentimiento: Consentimiento) -> None:
        with closing(self._fabrica_sesion()) as db:
            db.merge(
                ConsentimientoDB(
                    cliente_id=consentimiento.cliente_id,
                    consentimiento_id=consentimiento.consentimiento_id,
                    vence_en=consentimiento.vence_en,
                )
            )
            db.commit()

    def vigente(self, cliente_id: str, ahora: datetime) -> Consentimiento | None:
        with closing(self._fabrica_sesion()) as db:
            fila = db.get(ConsentimientoDB, cliente_id)
            if fila is None:
                return None
            vence_en = fila.vence_en
            if vence_en.tzinfo is None:  # SQLite devuelve fechas sin zona horaria.
                vence_en = vence_en.replace(tzinfo=ahora.tzinfo)
            if vence_en <= ahora:
                return None
            return Consentimiento(
                consentimiento_id=fila.consentimiento_id,
                cliente_id=fila.cliente_id,
                vence_en=vence_en,
            )
