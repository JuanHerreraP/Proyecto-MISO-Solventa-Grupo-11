"""Modelos persistentes de pólizas y enlaces temporales de certificado (HU07 / BPM-31)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructura.database import Base


class PolizaDB(Base):
    __tablename__ = "polizas"
    __table_args__ = (Index("ix_polizas_cliente_inicio", "cliente_id", "fecha_inicio"),)

    poliza_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    numero_poliza: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    cliente_id: Mapped[str] = mapped_column(String(50), nullable=False)
    cotizacion_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ramo: Mapped[str] = mapped_column(String(40), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    titular_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    titular_tipo_documento: Mapped[str] = mapped_column(String(20), nullable=False)
    titular_numero_documento: Mapped[str] = mapped_column(String(50), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    prima_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    cobertura_principal: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    codigo_verificacion: Mapped[str] = mapped_column(String(64), nullable=False)
    emitida_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EnlaceCertificadoDB(Base):
    """Solo se guarda la huella SHA-256 del token; el token en claro viaja en el enlace."""

    __tablename__ = "enlaces_certificado"

    huella_token: Mapped[str] = mapped_column(String(64), primary_key=True)
    poliza_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("polizas.poliza_id", ondelete="CASCADE"), nullable=False, index=True
    )
    cliente_id: Mapped[str] = mapped_column(String(50), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
