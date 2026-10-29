"""Tabla de siniestros (HU20). Relacionada con pólizas por `poliza_id`."""

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructura.database import Base


class SiniestroDB(Base):
    __tablename__ = "siniestros"
    __table_args__ = (
        Index("ix_siniestros_cliente", "cliente_id"),
        Index("ix_siniestros_poliza", "poliza_id"),
        Index("uq_siniestros_evento", "evento_id", unique=True),
    )

    siniestro_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(String(50), nullable=False)
    poliza_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("polizas.poliza_id"), nullable=False
    )
    origen: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    # Único cuando está presente (idempotencia de eventos de telemetría, HU20); NULL en manuales.
    evento_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fecha_evento: Mapped[date] = mapped_column(Date, nullable=False)
    hora_evento: Mapped[time] = mapped_column(Time, nullable=False)
    lugar: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    estimacion_danos: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    registrado_por: Mapped[str] = mapped_column(String(50), nullable=False)
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
