"""Tabla de asociación entre un asesor de ventas y los clientes que atiende (HU20).

Un asesor (`asesor_id`) queda vinculado a un cliente (`cliente_id`). La pareja es única:
no tiene sentido asociar dos veces al mismo cliente con el mismo asesor. Un cliente puede
ser atendido por varios asesores y un asesor atiende varios clientes.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructura.database import Base


class AsesorClienteDB(Base):
    __tablename__ = "asesor_cliente"
    __table_args__ = (
        Index("uq_asesor_cliente", "asesor_id", "cliente_id", unique=True),
        Index("ix_asesor_cliente_asesor", "asesor_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    asesor_id: Mapped[str] = mapped_column(String(50), nullable=False)
    cliente_id: Mapped[str] = mapped_column(String(50), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
