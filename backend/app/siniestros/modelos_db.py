"""Tablas de siniestros (HU20) y de sus evidencias (HU04 / EC10)."""

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructura.database import Base


class SiniestroDB(Base):
    __tablename__ = "siniestros"
    __table_args__ = (
        Index("ix_siniestros_cliente", "cliente_id"),
        Index("ix_siniestros_poliza", "poliza_id"),
        Index("uq_siniestros_evento", "evento_id", unique=True),
        # Un reintento desde la app con la misma Idempotency-Key no duplica el siniestro (HU04).
        Index("uq_siniestros_cliente_clave", "cliente_id", "clave_idempotencia", unique=True),
    )

    siniestro_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(String(50), nullable=False)
    poliza_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("polizas.poliza_id"), nullable=False
    )
    origen: Mapped[str] = mapped_column(String(20), nullable=False)
    # Columnas aditivas de HU04: nulas en los siniestros anteriores.
    tipo_siniestro: Mapped[str | None] = mapped_column(String(40), nullable=True)
    clave_idempotencia: Mapped[str | None] = mapped_column(String(80), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    # Único cuando está presente (idempotencia de eventos de telemetría, HU20); NULL en manuales.
    evento_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fecha_evento: Mapped[date] = mapped_column(Date, nullable=False)
    hora_evento: Mapped[time] = mapped_column(Time, nullable=False)
    lugar: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    estimacion_danos: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    registrado_por: Mapped[str] = mapped_column(String(50), nullable=False)
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Evaluación (HU15). Columnas aditivas: los siniestros anteriores quedan en NULL.
    monto_aprobado: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    evaluado_por: Mapped[str | None] = mapped_column(String(50), nullable=True)
    evaluado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_rechazo: Mapped[str | None] = mapped_column(String(500), nullable=True)


class EvidenciaSiniestroDB(Base):
    """Foto o video adjunto a un siniestro (HU04). Inmutable: no hay actualización ni borrado.

    El archivo vive en el almacén de documentos bajo `clave_almacenamiento`; aquí queda su
    huella SHA-256 para verificar en cada lectura que no fue alterado (EC10).
    """

    __tablename__ = "evidencias_siniestro"
    __table_args__ = (
        Index("ix_evidencias_siniestro", "siniestro_id"),
        # Reenviar el mismo archivo para el mismo siniestro no crea otra evidencia.
        Index("uq_evidencias_siniestro_huella", "siniestro_id", "huella_sha256", unique=True),
    )

    evidencia_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    siniestro_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("siniestros.siniestro_id"), nullable=False
    )
    cliente_id: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    tipo_contenido: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre_archivo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tamano_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    huella_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    clave_almacenamiento: Mapped[str] = mapped_column(String(200), nullable=False)
    capturada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latitud: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitud: Mapped[float | None] = mapped_column(Float, nullable=True)
    precision_metros: Mapped[float | None] = mapped_column(Float, nullable=True)
    subida_por: Mapped[str] = mapped_column(String(50), nullable=False)
    subida_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AccesoEvidenciaDB(Base):
    """Bitácora de auditoría de las evidencias (EC10): quién cargó, consultó o descargó qué.

    Solo se insertan filas; nada en la aplicación las modifica ni las borra.
    """

    __tablename__ = "auditoria_evidencias_siniestro"
    __table_args__ = (Index("ix_auditoria_evidencias_siniestro", "siniestro_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    siniestro_id: Mapped[str] = mapped_column(String(50), nullable=False)
    evidencia_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    accion: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(50), nullable=False)
    rol: Mapped[str] = mapped_column(String(40), nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    detalle: Mapped[str | None] = mapped_column(String(300), nullable=True)
    ocurrido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
