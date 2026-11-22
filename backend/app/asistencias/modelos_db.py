"""Tablas de la asistencia en sitio (HU06): prestadores, sus servicios y las solicitudes.

Los servicios del prestador se guardan normalizados en `prestador_servicios` (una fila por
servicio), no como una cadena separada por comas.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructura.database import Base


class PrestadorDB(Base):
    __tablename__ = "prestadores"
    __table_args__ = (Index("ix_prestadores_activo", "activo"),)

    prestador_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    direccion: Mapped[str] = mapped_column(String(300), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    latitud: Mapped[float] = mapped_column(Float, nullable=False)
    longitud: Mapped[float] = mapped_column(Float, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PrestadorServicioDB(Base):
    """Un servicio ofrecido por un prestador. Clave compuesta (prestador_id, servicio)."""

    __tablename__ = "prestador_servicios"
    __table_args__ = (Index("ix_prestador_servicios_servicio", "servicio"),)

    prestador_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("prestadores.prestador_id"), primary_key=True
    )
    servicio: Mapped[str] = mapped_column(String(40), primary_key=True)


class AsistenciaDB(Base):
    __tablename__ = "asistencias"
    __table_args__ = (
        Index("ix_asistencias_cliente", "cliente_id"),
        Index("ix_asistencias_poliza", "poliza_id"),
    )

    asistencia_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(String(50), nullable=False)
    poliza_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("polizas.poliza_id"), nullable=False
    )
    prestador_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("prestadores.prestador_id"), nullable=False
    )
    servicio: Mapped[str] = mapped_column(String(40), nullable=False)
    latitud: Mapped[float] = mapped_column(Float, nullable=False)
    longitud: Mapped[float] = mapped_column(Float, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    # Opcional para una evolución futura: una asistencia puede no tener siniestro (HU06).
    siniestro_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Seguimiento operativo (HU06 ampliación). Columnas aditivas: NULL en asistencias anteriores.
    aceptada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tiempo_estimado_llegada_minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)
