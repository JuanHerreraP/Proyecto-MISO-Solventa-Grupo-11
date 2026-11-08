"""Respuestas de la API de endosos (HU16 / BPM-68)."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.polizas.dominio.endosos import (
    MAX_BENEFICIARIOS,
    CambioEndoso,
    Endoso,
    PropuestaEndoso,
    TipoEndoso,
    admite_beneficiarios,
    coberturas_disponibles,
)
from app.polizas.dominio.modelos import Beneficiario, CoberturaPoliza, EstadoPoliza, Poliza


class ConceptoAjuste(str, Enum):
    COBRO = "COBRO"
    DEVOLUCION = "DEVOLUCION"
    SIN_AJUSTE = "SIN_AJUSTE"


def concepto_de(ajuste: Decimal) -> ConceptoAjuste:
    if ajuste > 0:
        return ConceptoAjuste.COBRO
    if ajuste < 0:
        return ConceptoAjuste.DEVOLUCION
    return ConceptoAjuste.SIN_AJUSTE


class CoberturaDisponible(BaseModel):
    codigo: str
    nombre: str
    descripcion: str
    suma_minima: Decimal
    suma_maxima: Decimal


class OpcionesModificacion(BaseModel):
    """Lo que el portal necesita para armar el formulario de modificación."""

    model_config = ConfigDict(extra="forbid")

    poliza_id: str
    numero_poliza: str
    nombre_ramo: str
    estado: EstadoPoliza
    modificable: bool
    fecha_inicio: date
    fecha_fin: date
    prima_total: Decimal
    moneda: str
    cobertura_principal: CoberturaPoliza
    coberturas_opcionales: list[CoberturaPoliza]
    coberturas_disponibles: list[CoberturaDisponible]
    admite_beneficiarios: bool
    max_beneficiarios: int
    beneficiarios: list[Beneficiario]


class PropuestaVista(BaseModel):
    model_config = ConfigDict(extra="forbid")

    poliza_id: str
    tipo: TipoEndoso
    cambios: list[CambioEndoso]
    beneficiarios: list[Beneficiario]
    coberturas_opcionales: list[CoberturaPoliza]
    fecha_efecto: date
    dias_vigencia: int
    dias_restantes: int
    prima_anterior: Decimal
    ajuste_prima: Decimal
    concepto_ajuste: ConceptoAjuste
    prima_nueva: Decimal
    moneda: str


class EndosoVista(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endoso_id: str
    poliza_id: str
    numero_endoso: int
    tipo: TipoEndoso
    rol_solicitante: str
    fecha_efecto: date
    creado_en: datetime
    dias_vigencia: int
    dias_restantes: int
    prima_anterior: Decimal
    ajuste_prima: Decimal
    concepto_ajuste: ConceptoAjuste
    prima_nueva: Decimal
    moneda: str
    cambios: list[CambioEndoso]
    coberturas_opcionales: list[CoberturaPoliza]
    beneficiarios: list[Beneficiario]
    huella_documento: str


class HistorialEndosos(BaseModel):
    endosos: list[EndosoVista]


def a_opciones(poliza: Poliza, hoy: date) -> OpcionesModificacion:
    maxima_principal = poliza.cobertura_principal.suma_asegurada
    disponibles = [
        CoberturaDisponible(
            codigo=d.codigo,
            nombre=d.nombre,
            descripcion=d.descripcion,
            suma_minima=d.suma_minima,
            suma_maxima=min(d.suma_maxima, maxima_principal)
            if d.hasta_suma_principal
            else d.suma_maxima,
        )
        for d in coberturas_disponibles(poliza.ramo)
    ]
    estado = poliza.estado_en(hoy)
    return OpcionesModificacion(
        poliza_id=poliza.poliza_id,
        numero_poliza=poliza.numero_poliza,
        nombre_ramo=poliza.nombre_ramo,
        estado=estado,
        modificable=estado is EstadoPoliza.VIGENTE,
        fecha_inicio=poliza.fecha_inicio,
        fecha_fin=poliza.fecha_fin,
        prima_total=poliza.prima_total,
        moneda=poliza.moneda,
        cobertura_principal=poliza.cobertura_principal,
        coberturas_opcionales=poliza.coberturas_opcionales,
        coberturas_disponibles=disponibles,
        admite_beneficiarios=admite_beneficiarios(poliza.ramo),
        max_beneficiarios=MAX_BENEFICIARIOS,
        beneficiarios=poliza.beneficiarios,
    )


def a_propuesta(propuesta: PropuestaEndoso) -> PropuestaVista:
    datos = propuesta.model_dump(
        exclude={"prima_opcionales_anterior", "prima_opcionales_nueva", "version_tarifas"}
    )
    return PropuestaVista(**datos, concepto_ajuste=concepto_de(propuesta.ajuste_prima))


def a_endoso(endoso: Endoso) -> EndosoVista:
    datos = endoso.model_dump(
        include=set(EndosoVista.model_fields) - {"concepto_ajuste"},
    )
    return EndosoVista(**datos, concepto_ajuste=concepto_de(endoso.ajuste_prima))
