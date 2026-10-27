"""Lo que la billetera expone al cliente. Nunca incluye el documento completo del titular."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.polizas.dominio.modelos import EstadoPoliza, Poliza, RamoPoliza


class PolizaEnBilletera(BaseModel):
    poliza_id: str
    numero_poliza: str
    ramo: RamoPoliza
    nombre_ramo: str
    estado: EstadoPoliza
    activa: bool
    fecha_inicio: date
    fecha_fin: date
    cobertura_principal: str


class Billetera(BaseModel):
    polizas: list[PolizaEnBilletera]
    total_vigentes: int
    total_inactivas: int


class CertificadoPoliza(BaseModel):
    poliza_id: str
    numero_poliza: str
    ramo: RamoPoliza
    nombre_ramo: str
    estado: EstadoPoliza
    activa: bool
    titular: str
    documento_titular: str
    fecha_inicio: date
    fecha_fin: date
    cobertura_principal: str
    descripcion_cobertura: str | None = None
    suma_asegurada: Decimal
    prima_total: Decimal
    moneda: str
    emitida_en: datetime
    contenido_qr: str


class EnlaceCompartido(BaseModel):
    url: str
    expira_en: datetime


class CertificadoCompartido(BaseModel):
    """Versión pública del certificado: sin prima ni identificadores internos."""

    numero_poliza: str
    nombre_ramo: str
    estado: EstadoPoliza
    activa: bool
    titular: str
    documento_titular: str
    fecha_inicio: date
    fecha_fin: date
    cobertura_principal: str
    suma_asegurada: Decimal
    moneda: str
    enlace_expira_en: datetime


def a_poliza_en_billetera(poliza: Poliza, hoy: date) -> PolizaEnBilletera:
    estado = poliza.estado_en(hoy)
    return PolizaEnBilletera(
        poliza_id=poliza.poliza_id,
        numero_poliza=poliza.numero_poliza,
        ramo=poliza.ramo,
        nombre_ramo=poliza.nombre_ramo,
        estado=estado,
        activa=estado is EstadoPoliza.VIGENTE,
        fecha_inicio=poliza.fecha_inicio,
        fecha_fin=poliza.fecha_fin,
        cobertura_principal=poliza.cobertura_principal.nombre,
    )


def a_certificado(poliza: Poliza, hoy: date) -> CertificadoPoliza:
    estado = poliza.estado_en(hoy)
    return CertificadoPoliza(
        poliza_id=poliza.poliza_id,
        numero_poliza=poliza.numero_poliza,
        ramo=poliza.ramo,
        nombre_ramo=poliza.nombre_ramo,
        estado=estado,
        activa=estado is EstadoPoliza.VIGENTE,
        titular=poliza.titular_nombre,
        documento_titular=poliza.documento_enmascarado,
        fecha_inicio=poliza.fecha_inicio,
        fecha_fin=poliza.fecha_fin,
        cobertura_principal=poliza.cobertura_principal.nombre,
        descripcion_cobertura=poliza.cobertura_principal.descripcion,
        suma_asegurada=poliza.cobertura_principal.suma_asegurada,
        prima_total=poliza.prima_total,
        moneda=poliza.moneda,
        emitida_en=poliza.emitida_en,
        contenido_qr=poliza.contenido_qr,
    )


def a_certificado_compartido(
    poliza: Poliza, hoy: date, enlace_expira_en: datetime
) -> CertificadoCompartido:
    estado = poliza.estado_en(hoy)
    return CertificadoCompartido(
        numero_poliza=poliza.numero_poliza,
        nombre_ramo=poliza.nombre_ramo,
        estado=estado,
        activa=estado is EstadoPoliza.VIGENTE,
        titular=poliza.titular_nombre,
        documento_titular=poliza.documento_enmascarado,
        fecha_inicio=poliza.fecha_inicio,
        fecha_fin=poliza.fecha_fin,
        cobertura_principal=poliza.cobertura_principal.nombre,
        suma_asegurada=poliza.cobertura_principal.suma_asegurada,
        moneda=poliza.moneda,
        enlace_expira_en=enlace_expira_en,
    )
