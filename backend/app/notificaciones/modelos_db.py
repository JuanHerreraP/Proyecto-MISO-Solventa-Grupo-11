"""Persistencia de las notificaciones, los dispositivos push y las preferencias."""

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructura.database import Base


class NotificacionDB(Base):
    __tablename__ = "notificaciones"
    __table_args__ = (
        # Un evento se registra una sola vez por cliente.
        UniqueConstraint("cliente_id", "clave", name="uq_notificaciones_cliente_clave"),
        Index("ix_notificaciones_cliente_creada", "cliente_id", "creada_en"),
        Index("ix_notificaciones_cliente_tipo_dia", "cliente_id", "tipo", "dia"),
    )

    notificacion_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    clave: Mapped[str] = mapped_column(String(150), nullable=False)
    titulo: Mapped[str] = mapped_column(String(120), nullable=False)
    cuerpo: Mapped[str] = mapped_column(String(400), nullable=False)
    datos: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    dia: Mapped[date] = mapped_column(Date, nullable=False)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    leida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DispositivoPushDB(Base):
    __tablename__ = "dispositivos_push"
    __table_args__ = (Index("ix_dispositivos_push_cliente_activo", "cliente_id", "activo"),)

    dispositivo_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(String(50), nullable=False)
    # Un token pertenece a un solo dispositivo: si otro cliente inicia sesión en el mismo
    # teléfono, el token pasa a él.
    token: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    plataforma: Mapped[str] = mapped_column(String(20), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PreferenciaNotificacionDB(Base):
    __tablename__ = "preferencias_notificacion"

    cliente_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    push_habilitado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
