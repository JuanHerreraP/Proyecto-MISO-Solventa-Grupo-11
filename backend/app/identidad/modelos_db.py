"""Modelos persistentes del módulo de identidad."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructura.database import Base


class UsuarioDB(Base):
    __tablename__ = "usuarios"

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