"""Adaptadores de fuentes externas.

Cada adaptador conoce el contrato de su proveedor y lo traduce al modelo interno. Nada del
contrato externo sale de este módulo.
"""

import hashlib

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.perfilamiento.dominio.modelos import (
    NivelRiesgoZona,
    SenalesOpenData,
    SenalesOpenFinance,
)
from app.perfilamiento.enriquecimiento.modelos import TipoFuente
from app.perfilamiento.enriquecimiento.puertos import FuenteNoDisponible

MESES_ESTABILIDAD_PLENA = 60
UMBRAL_ZONA_MEDIO = 34
UMBRAL_ZONA_ALTO = 67


async def _obtener_json(cliente: httpx.AsyncClient, ruta: str, proveedor: str) -> dict:
    try:
        respuesta = await cliente.get(ruta)
    except httpx.TimeoutException:
        raise FuenteNoDisponible(proveedor, "tiempo de espera agotado") from None
    except httpx.HTTPError as error:
        raise FuenteNoDisponible(proveedor, f"error de conexión ({type(error).__name__})") from None

    if respuesta.status_code != httpx.codes.OK:
        raise FuenteNoDisponible(proveedor, f"respuesta HTTP {respuesta.status_code}")
    try:
        cuerpo = respuesta.json()
    except ValueError:
        raise FuenteNoDisponible(proveedor, "respuesta que no es JSON") from None
    if not isinstance(cuerpo, dict):
        raise FuenteNoDisponible(proveedor, "respuesta con formato inesperado")
    return cuerpo


class _HistorialPagos(BaseModel):
    on_time_payments: int = Field(ge=0)
    total_payments: int = Field(gt=0)


class _RespuestaOpenFinance(BaseModel):
    payment_history: _HistorialPagos
    monthly_income: float = Field(gt=0)
    monthly_debt_payments: float = Field(ge=0)


class AdaptadorOpenFinance:
    """Agregador de Open Finance: historial de pagos y capacidad de endeudamiento."""

    tipo = TipoFuente.OPEN_FINANCE

    def __init__(self, cliente: httpx.AsyncClient, proveedor: str = "open-finance"):
        self._cliente = cliente
        self.proveedor = proveedor

    async def consultar(self, cliente_id: str) -> SenalesOpenFinance:
        cuerpo = await _obtener_json(self._cliente, f"/v1/customers/{cliente_id}", self.proveedor)
        try:
            datos = _RespuestaOpenFinance.model_validate(cuerpo)
            pagos = datos.payment_history
            return SenalesOpenFinance(
                comportamiento_pago=min(pagos.on_time_payments / pagos.total_payments, 1.0),
                nivel_endeudamiento=min(datos.monthly_debt_payments / datos.monthly_income, 1.0),
            )
        except ValidationError:
            raise FuenteNoDisponible(self.proveedor, "respuesta con contenido inválido") from None


class _Zona(BaseModel):
    indice_riesgo: float = Field(ge=0, le=100)


class _RespuestaOpenData(BaseModel):
    antiguedad_laboral_meses: int = Field(ge=0)
    antiguedad_residencia_meses: int = Field(ge=0)
    zona_inmueble: _Zona


class AdaptadorOpenData:
    """Fuente pública de Open Data: datos sociodemográficos y del inmueble."""

    tipo = TipoFuente.OPEN_DATA

    def __init__(self, cliente: httpx.AsyncClient, proveedor: str = "open-data"):
        self._cliente = cliente
        self.proveedor = proveedor

    async def consultar(self, cliente_id: str) -> SenalesOpenData:
        cuerpo = await _obtener_json(self._cliente, f"/ciudadanos/{cliente_id}", self.proveedor)
        try:
            datos = _RespuestaOpenData.model_validate(cuerpo)
            meses = (datos.antiguedad_laboral_meses + datos.antiguedad_residencia_meses) / 2
            return SenalesOpenData(
                estabilidad=min(meses / MESES_ESTABILIDAD_PLENA, 1.0),
                riesgo_zona=clasificar_zona(datos.zona_inmueble.indice_riesgo),
            )
        except ValidationError:
            raise FuenteNoDisponible(self.proveedor, "respuesta con contenido inválido") from None


def clasificar_zona(indice_riesgo: float) -> NivelRiesgoZona:
    if indice_riesgo < UMBRAL_ZONA_MEDIO:
        return NivelRiesgoZona.BAJO
    if indice_riesgo < UMBRAL_ZONA_ALTO:
        return NivelRiesgoZona.MEDIO
    return NivelRiesgoZona.ALTO


def _semilla(cliente_id: str, sal: str) -> list[float]:
    """Valores entre 0 y 1 derivados del cliente, estables entre ejecuciones."""
    resumen = hashlib.sha256(f"{sal}:{cliente_id}".encode()).digest()
    return [byte / 255 for byte in resumen[:4]]


class FuenteSimuladaOpenFinance:
    """Simulador en proceso para desarrollo y demostraciones. No usar en producción."""

    tipo = TipoFuente.OPEN_FINANCE
    proveedor = "simulador-open-finance"

    async def consultar(self, cliente_id: str) -> SenalesOpenFinance:
        a, b, *_ = _semilla(cliente_id, "of")
        return SenalesOpenFinance(
            comportamiento_pago=round(0.3 + 0.7 * a, 4),
            nivel_endeudamiento=round(0.85 * b, 4),
        )


class FuenteSimuladaOpenData:
    """Simulador en proceso para desarrollo y demostraciones. No usar en producción."""

    tipo = TipoFuente.OPEN_DATA
    proveedor = "simulador-open-data"

    async def consultar(self, cliente_id: str) -> SenalesOpenData:
        a, b, *_ = _semilla(cliente_id, "od")
        return SenalesOpenData(estabilidad=round(a, 4), riesgo_zona=clasificar_zona(100 * b))
