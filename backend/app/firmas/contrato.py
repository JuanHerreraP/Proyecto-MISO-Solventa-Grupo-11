"""Contrato prellenado y su huella (HU14 / BPM-60).

El contrato se arma una sola vez, cuando el pago queda aprobado, y se guarda tal cual se
presentó. La huella SHA-256 se calcula sobre su forma canónica: si alguien altera el
contrato guardado, la huella deja de coincidir (EC10).
"""

import hashlib
import json
from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field

from app.cotizaciones.dominio.catalogo import consultar_ramo
from app.cotizaciones.dominio.modelos import RamoSeguro

VERSION_PLANTILLA = "2026.10.2"

_CLAUSULAS_GENERALES = (
    "El tomador declara que la información suministrada es veraz y completa; la inexactitud "
    "o reticencia puede producir la nulidad relativa del contrato.",
    "La prima fue pagada en su totalidad mediante el recaudo inicial identificado en este "
    "documento.",
    "El tomador puede revocar el contrato en cualquier momento; la devolución de la prima no "
    "devengada se rige por las condiciones generales del ramo.",
    "La firma electrónica de este documento tiene la misma validez que la firma manuscrita "
    "(Ley 527 de 1999 y Decreto 2364 de 2012).",
)

# Vida hipotecario: la cotización trae el crédito que respalda el seguro (banco aliado, EC02).
NOMBRE_VIDA_HIPOTECARIO = "Seguro de vida hipotecario"
CAMPO_CREDITO_HIPOTECARIO = "valor_credito"

_CLAUSULAS_VIDA = (
    "El beneficio se paga a los beneficiarios designados por el asegurado o, en su defecto, "
    "a sus herederos legales.",
    "Se excluye el suicidio ocurrido durante el primer año de vigencia.",
)

_CLAUSULAS_VIDA_HIPOTECARIO = (
    "El beneficiario a título oneroso es la entidad financiera que otorgó el crédito "
    "hipotecario, hasta por el saldo insoluto de la deuda a la fecha del siniestro.",
    "El remanente de la suma asegurada, si lo hay, se paga a los beneficiarios designados "
    "por el asegurado o, en su defecto, a sus herederos legales.",
    "Se excluye el suicidio ocurrido durante el primer año de vigencia.",
)

CLAUSULAS_POR_RAMO: dict[RamoSeguro, tuple[str, ...]] = {
    RamoSeguro.VIDA: _CLAUSULAS_VIDA,
    RamoSeguro.VIAJE: (
        "La cobertura opera únicamente durante las fechas del viaje declaradas al cotizar.",
    ),
    RamoSeguro.PROTECCION_DISPOSITIVOS: (
        "La cobertura aplica al dispositivo identificado al cotizar; el deducible se descuenta "
        "de cada indemnización.",
    ),
    RamoSeguro.PARAMETRICO: (
        "La indemnización se activa al cumplirse el índice paramétrico pactado, sin necesidad "
        "de demostrar la pérdida.",
    ),
}


class CoberturaContrato(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    codigo: str
    nombre: str
    suma_asegurada: Decimal
    descripcion: str | None = None


class TitularContrato(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nombre_completo: str = Field(min_length=2, max_length=200)
    tipo_documento: str = Field(min_length=2, max_length=20)
    numero_documento: str = Field(min_length=3, max_length=50)
    email: EmailStr
    celular: str | None = Field(default=None, max_length=30)


class ContratoSeguro(BaseModel):
    """Condiciones particulares que el cliente revisa y firma."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version_plantilla: str
    cotizacion_id: str
    ramo: RamoSeguro
    nombre_ramo: str
    titular: TitularContrato
    cobertura_principal: CoberturaContrato
    datos_riesgo: dict[str, object]
    prima_total: Decimal
    moneda: str
    pago_id: str
    referencia_pago: str | None
    fecha_pago: AwareDatetime
    clausulas: tuple[str, ...]

    def contenido_canonico(self) -> bytes:
        """Serialización estable: mismas condiciones, mismos bytes, misma huella."""
        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def huella(self) -> str:
        return hashlib.sha256(self.contenido_canonico()).hexdigest()


def es_vida_hipotecario(ramo: RamoSeguro, datos_riesgo: dict[str, object]) -> bool:
    return ramo is RamoSeguro.VIDA and CAMPO_CREDITO_HIPOTECARIO in datos_riesgo


def nombre_ramo_de(ramo: RamoSeguro, datos_riesgo: dict[str, object]) -> str:
    """El mismo nombre que el cliente vio al cotizar (catálogo de HU03)."""
    if es_vida_hipotecario(ramo, datos_riesgo):
        return NOMBRE_VIDA_HIPOTECARIO
    return consultar_ramo(ramo).nombre


def clausulas_de(ramo: RamoSeguro, datos_riesgo: dict[str, object]) -> tuple[str, ...]:
    if es_vida_hipotecario(ramo, datos_riesgo):
        particulares = _CLAUSULAS_VIDA_HIPOTECARIO
    else:
        particulares = CLAUSULAS_POR_RAMO.get(ramo, ())
    return particulares + _CLAUSULAS_GENERALES
