"""Modelos persistentes del módulo de identidad."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructura.database import Base


class UsuarioDB(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        Index(
            "uq_usuarios_tipo_documento_numero_documento",
            "tipo_documento",
            "numero_documento",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    nombre: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    apellido: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    rol: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    tipo_documento: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    numero_documento: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    celular: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    fecha_nacimiento: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    kyc_validado: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    referencia_kyc: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    consentimiento_kyc: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class EventoAutenticacionDB(Base):
    __tablename__ = "eventos_autenticacion"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    tipo_evento: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    exitoso: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    detalle: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    ip: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )


class SesionRefreshDB(Base):
    """Refresh token emitido. Permite rotarlo, revocarlo y detectar su reutilización."""

    __tablename__ = "sesiones_refresh"

    ultima_actividad: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    jti: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    fecha_emision: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    fecha_expiracion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revocada: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    fecha_revocacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    motivo_revocacion: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    reemplazada_por: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )
