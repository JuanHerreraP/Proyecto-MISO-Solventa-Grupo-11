"""Persistencia de pagos (HU13)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructura.database import Base


class PagoDB(Base):
    __tablename__ = "pagos"
    __table_args__ = (
        UniqueConstraint("cliente_id", "idempotency_key", name="uq_pagos_cliente_llave"),
        Index("ix_pagos_cotizacion_estado", "cotizacion_id", "estado"),
        # Una cotización solo se cobra una vez: la base impide dos pagos aprobados aunque dos
        # solicitudes simultáneas pasen la verificación del servicio (HU21).
        Index(
            "uq_pagos_cotizacion_aprobado",
            "cotizacion_id",
            unique=True,
            postgresql_where=text("estado = 'APROBADO'"),
            sqlite_where=text("estado = 'APROBADO'"),
        ),
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


class ComprobanteDB(Base):
    """Comprobante de un pago aprobado (HU21). Un pago tiene un solo comprobante."""

    __tablename__ = "comprobantes"

    comprobante_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    numero: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    pago_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    cliente_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    cotizacion_id: Mapped[str] = mapped_column(String(50), nullable=False)
    concepto: Mapped[str] = mapped_column(String(15), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)
    poliza_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    numero_poliza: Mapped[str | None] = mapped_column(String(40), nullable=True)
    nombre_ramo: Mapped[str] = mapped_column(String(120), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    metodo: Mapped[str] = mapped_column(String(10), nullable=False)
    referencia_pasarela: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pagado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    emitido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
