"""Modelos persistentes de pólizas, certificados, documentos y endosos (HU07, HU12, HU16)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
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
    # Columnas aditivas de HU16: las pólizas emitidas antes del cambio quedan en NULL.
    coberturas_opcionales: Mapped[list[dict[str, object]] | None] = mapped_column(
        JSON, nullable=True
    )
    beneficiarios: Mapped[list[dict[str, object]] | None] = mapped_column(JSON, nullable=True)
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


class DocumentoPolizaDB(Base):
    """PDF emitido de una póliza: dónde está guardado y su huella SHA-256 (HU12)."""

    __tablename__ = "documentos_poliza"

    poliza_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("polizas.poliza_id", ondelete="CASCADE"), primary_key=True
    )
    clave_almacenamiento: Mapped[str] = mapped_column(String(200), nullable=False)
    huella_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bienvenida_enviada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notificada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EndosoDB(Base):
    """Endoso de una póliza: qué cambió, quién lo pidió, el ajuste de prima y su PDF (HU16).

    Un endoso no se modifica ni se borra. El número es consecutivo por póliza y la restricción
    única evita que dos confirmaciones simultáneas generen el mismo endoso.
    """

    __tablename__ = "endosos"
    __table_args__ = (
        UniqueConstraint("poliza_id", "numero_endoso", name="uq_endosos_poliza_numero"),
        UniqueConstraint("poliza_id", "clave_idempotencia", name="uq_endosos_poliza_clave"),
    )

    endoso_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    poliza_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("polizas.poliza_id", ondelete="CASCADE"), nullable=False, index=True
    )
    numero_endoso: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    solicitado_por: Mapped[str] = mapped_column(String(50), nullable=False)
    rol_solicitante: Mapped[str] = mapped_column(String(40), nullable=False)
    clave_idempotencia: Mapped[str | None] = mapped_column(String(100), nullable=True)
    huella_solicitud: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_solicitante: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    fecha_efecto: Mapped[date] = mapped_column(Date, nullable=False)
    dias_vigencia: Mapped[int] = mapped_column(Integer, nullable=False)
    dias_restantes: Mapped[int] = mapped_column(Integer, nullable=False)
    prima_anterior: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    ajuste_prima: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    prima_nueva: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    cambios: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    coberturas_opcionales: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    beneficiarios: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    clave_documento: Mapped[str] = mapped_column(String(200), nullable=False)
    huella_documento: Mapped[str] = mapped_column(String(64), nullable=False)
    tamano_documento: Mapped[int] = mapped_column(Integer, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CancelacionDB(Base):
    """Cancelación de una póliza: motivo, quién la pidió y el saldo a favor calculado (HU22).

    Una póliza se cancela una sola vez (restricción única por póliza) y el registro no se
    modifica. El saldo queda con devolución pendiente; gestionarla es otra historia.
    """

    __tablename__ = "cancelaciones"
    __table_args__ = (
        UniqueConstraint("poliza_id", name="uq_cancelaciones_poliza"),
        UniqueConstraint("poliza_id", "clave_idempotencia", name="uq_cancelaciones_poliza_clave"),
    )

    cancelacion_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    poliza_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("polizas.poliza_id", ondelete="CASCADE"), nullable=False, index=True
    )
    motivo: Mapped[str] = mapped_column(String(40), nullable=False)
    detalle: Mapped[str | None] = mapped_column(String(300), nullable=True)
    solicitado_por: Mapped[str] = mapped_column(String(50), nullable=False)
    rol_solicitante: Mapped[str] = mapped_column(String(40), nullable=False)
    clave_idempotencia: Mapped[str | None] = mapped_column(String(100), nullable=True)
    huella_solicitud: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_solicitante: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    fecha_efecto: Mapped[date] = mapped_column(Date, nullable=False)
    dias_totales: Mapped[int] = mapped_column(Integer, nullable=False)
    dias_no_transcurridos: Mapped[int] = mapped_column(Integer, nullable=False)
    prima_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    saldo_estimado: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    estado_devolucion: Mapped[str] = mapped_column(String(20), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RenovacionDB(Base):
    """Renovación de una póliza: su cotización de pago y los periodos anterior y nuevo (HU22).

    El identificador sale de la póliza y del inicio del nuevo periodo, así que una póliza se
    renueva una sola vez por periodo. Al aprobarse el pago, la póliza toma el nuevo periodo y
    este registro conserva el anterior, necesario para calcular el saldo si luego se cancela.
    """

    __tablename__ = "renovaciones"
    __table_args__ = (
        UniqueConstraint("poliza_id", "nuevo_inicio", name="uq_renovaciones_poliza_periodo"),
        UniqueConstraint("poliza_id", "clave_idempotencia", name="uq_renovaciones_poliza_clave"),
    )

    renovacion_id: Mapped[str] = mapped_column(String(70), primary_key=True)
    poliza_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("polizas.poliza_id", ondelete="CASCADE"), nullable=False, index=True
    )
    cotizacion_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    anterior_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    anterior_fin: Mapped[date] = mapped_column(Date, nullable=False)
    anterior_prima: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    nuevo_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    nuevo_fin: Mapped[date] = mapped_column(Date, nullable=False)
    prima_principal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    prima_opcionales: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    prima_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    vigente_hasta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pago_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    solicitado_por: Mapped[str] = mapped_column(String(50), nullable=False)
    rol_solicitante: Mapped[str] = mapped_column(String(40), nullable=False)
    clave_idempotencia: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip_solicitante: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aplicada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_no_aplicada: Mapped[str | None] = mapped_column(String(200), nullable=True)
