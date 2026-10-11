"""Modelos persistentes del módulo de socios de distribución."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructura.database import Base


class SocioDistribucionDB(Base):
    __tablename__ = "socios_distribucion"

    socio_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    nit: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    razon_social: Mapped[str] = mapped_column(String(160), nullable=False)
    contactos_tecnicos: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    pais_operacion: Mapped[str] = mapped_column(String(2), nullable=False)
    tipos_seguros_autorizados: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    endpoints_autorizados: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EventoAuditoriaSocioDB(Base):
    __tablename__ = "eventos_auditoria_socios"

    auditoria_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    socio_id: Mapped[str] = mapped_column(
        ForeignKey("socios_distribucion.socio_id"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    accion: Mapped[str] = mapped_column(String(30), nullable=False)
    campos_modificados: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
