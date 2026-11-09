"""Persistencia del proceso de firma (HU14 / BPM-60)."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructura.database import Base


class ProcesoFirmaDB(Base):
    __tablename__ = "firmas_contrato"

    firma_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    cotizacion_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    pago_id: Mapped[str] = mapped_column(String(50), nullable=False)
    cliente_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(12), nullable=False)
    contrato: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    huella_documento: Mapped[str] = mapped_column(String(64), nullable=False)

    otp_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    otp_canal: Mapped[str | None] = mapped_column(String(10), nullable=True)
    otp_destino: Mapped[str | None] = mapped_column(String(255), nullable=True)
    otp_emitido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    otp_expira_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    intentos_fallidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    envios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    referencia_envio: Mapped[str | None] = mapped_column(String(100), nullable=True)

    firmado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    firmante_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ip_firmante: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    referencia_proveedor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sello_proveedor: Mapped[str | None] = mapped_column(String(200), nullable=True)

    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
