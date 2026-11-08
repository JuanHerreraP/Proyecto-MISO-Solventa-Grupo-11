"""Tablas de desembolsos y cuentas de destino (HU15)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructura.database import Base


class DesembolsoDB(Base):
    """Uno por siniestro: la restricción única evita pagar dos veces la misma indemnización."""

    __tablename__ = "desembolsos"
    __table_args__ = (
        Index("uq_desembolsos_siniestro", "siniestro_id", unique=True),
        Index("ix_desembolsos_cliente", "cliente_id"),
    )

    desembolso_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    siniestro_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("siniestros.siniestro_id"), nullable=False
    )
    poliza_id: Mapped[str] = mapped_column(String(50), nullable=False)
    cliente_id: Mapped[str] = mapped_column(String(50), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    medio: Mapped[str] = mapped_column(String(20), nullable=False)
    destino: Mapped[str | None] = mapped_column(String(120), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    intento: Mapped[int] = mapped_column(Integer, nullable=False)
    referencia_transaccion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    codigo_retiro: Mapped[str | None] = mapped_column(String(20), nullable=True)
    motivo_fallo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CuentaDesembolsoDB(Base):
    """Solo el token de la red y los últimos dígitos: nunca el número de cuenta completo."""

    __tablename__ = "cuentas_desembolso"

    cliente_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    codigo_banco: Mapped[str] = mapped_column(String(4), nullable=False)
    tipo_cuenta: Mapped[str] = mapped_column(String(20), nullable=False)
    ultimos_digitos: Mapped[str] = mapped_column(String(4), nullable=False)
    token_cuenta: Mapped[str] = mapped_column(String(100), nullable=False)
    registrada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actualizada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
