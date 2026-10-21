"""Modelos persistentes del módulo de cotizaciones (HU03 / BPM-156)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructura.database import Base


class CotizacionDB(Base):
    """Representación relacional de una cotización y su resultado comercial."""

    __tablename__ = "cotizaciones"
    __table_args__ = (Index("ix_cotizaciones_cliente_creada", "cliente_id", "creada_en"),)

    cotizacion_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(String(50), nullable=False)
    ramo: Mapped[str] = mapped_column(String(40), nullable=False)
    datos_riesgo: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    prima_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    cobertura_principal: Mapped[dict[str, object] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    perfil_riesgo_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    asesor_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    socio_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vigente_hasta: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
