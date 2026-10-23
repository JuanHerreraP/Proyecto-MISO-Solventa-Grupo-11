"""Persistencia de pagos (HU13)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructura.database import Base


class PagoDB(Base):
    __tablename__ = "pagos"
    __table_args__ = (
        UniqueConstraint("cliente_id", "idempotency_key", name="uq_pagos_cliente_llave"),
        Index("ix_pagos_cotizacion_estado", "cotizacion_id", "estado"),
    )

    pago_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    cotizacion_id: Mapped[str] = mapped_column(String(50), nullable=False)
    cliente_id: Mapped[str] = mapped_column(String(50), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    huella_solicitud: Mapped[str] = mapped_column(String(64), nullable=False)
    metodo: Mapped[str] = mapped_column(String(10), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False)
    referencia_pasarela: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    url_redireccion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    motivo_rechazo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
