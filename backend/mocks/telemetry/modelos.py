"""Modelos del proveedor externo simulado de telemetría (HU20).

Este módulo define las solicitudes de simulación (lo que recibe el mock) y la construcción
de los eventos salientes (lo que se empuja hacia Solventa). El proveedor NO conoce el dominio
interno de Solventa: no sabe de pólizas, umbrales, vigencias ni clientes. Solo observa un
valor y lo reporta.

La arquitectura permite agregar nuevos tipos de evento más adelante registrando un nuevo
constructor sin reescribir el resto del servicio.
"""

import re
import unicodedata
import uuid
from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class SolicitudRetrasoVuelo(BaseModel):
    """Simulación de un retraso de vuelo recibida por el mock.

    El cliente de simulación NO suministra `evento_id`: el proveedor lo genera.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    numero_vuelo: str = Field(min_length=1, max_length=20)
    retraso_minutos: int = Field(ge=0)
    aeropuerto: str = Field(min_length=1, max_length=10)
    fecha_evento: AwareDatetime


class SolicitudEventoClimatico(BaseModel):
    """Simulación de un evento climático recibida por el mock.

    Inicialmente solo se admite `tipo_medicion = PRECIPITACION`, pero la estructura permite
    incorporar otros parámetros climáticos después.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ubicacion: str = Field(min_length=1, max_length=120)
    tipo_medicion: str = Field(min_length=1, max_length=40)
    valor: float = Field(ge=0)
    unidad: str = Field(min_length=1, max_length=20)
    fecha_evento: AwareDatetime


class EventoTelemetria(BaseModel):
    """Evento genérico que el proveedor empuja hacia Solventa.

    Es deliberadamente plano y descriptivo. Solventa es quien interpreta `valor_observado`
    contra el umbral contratado; el proveedor solo informa la observación.
    """

    model_config = ConfigDict(extra="allow")

    evento_id: str
    tipo_evento: str
    valor_observado: float
    unidad: str
    fecha_evento: str
    fuente: str


def _slug(valor: str) -> str:
    """Normaliza un texto para el identificador: sin tildes, mayúsculas y solo [A-Z0-9].

    Ej.: "Bogotá" -> "BOGOTA". Los acentos se transliteran a su letra base para que el
    identificador sea estable y legible.
    """
    sin_tildes = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode("ascii")
    limpio = re.sub(r"[^A-Za-z0-9]", "", sin_tildes).upper()
    return limpio or "NA"


def _marca_fecha(fecha: datetime) -> str:
    return fecha.strftime("%Y%m%d")


def _sufijo() -> str:
    """Fragmento aleatorio corto y estable por evento."""
    return uuid.uuid4().hex[:8]


def generar_id_vuelo(numero_vuelo: str, fecha: datetime) -> str:
    """Ej.: FLIGHT-AV123-20261026-acde1234."""
    return f"FLIGHT-{_slug(numero_vuelo)}-{_marca_fecha(fecha)}-{_sufijo()}"


def generar_id_clima(ubicacion: str, fecha: datetime) -> str:
    """Ej.: WEATHER-BOGOTA-20261026-acde1234."""
    return f"WEATHER-{_slug(ubicacion)}-{_marca_fecha(fecha)}-{_sufijo()}"


def construir_evento_vuelo(solicitud: SolicitudRetrasoVuelo, evento_id: str) -> EventoTelemetria:
    """Transforma la simulación de vuelo en el evento saliente para Solventa."""
    return EventoTelemetria(
        evento_id=evento_id,
        tipo_evento="RETRASO_VUELO",
        numero_vuelo=solicitud.numero_vuelo,
        valor_observado=float(solicitud.retraso_minutos),
        unidad="MINUTOS",
        ubicacion=solicitud.aeropuerto,
        fecha_evento=solicitud.fecha_evento.isoformat(),
        fuente="MOCK_FLIGHT_PROVIDER",
    )


def construir_evento_clima(solicitud: SolicitudEventoClimatico, evento_id: str) -> EventoTelemetria:
    """Transforma la simulación climática en el evento saliente para Solventa."""
    return EventoTelemetria(
        evento_id=evento_id,
        tipo_evento="EVENTO_CLIMATICO",
        ubicacion=solicitud.ubicacion,
        parametro=solicitud.tipo_medicion,
        valor_observado=solicitud.valor,
        unidad=solicitud.unidad,
        fecha_evento=solicitud.fecha_evento.isoformat(),
        fuente="MOCK_WEATHER_PROVIDER",
    )


class RespuestaSimulacion(BaseModel):
    """Lo que el mock responde a quien dispara la simulación."""

    evento_id: str
    tipo_evento: str
    enviado: bool
    solventa_status: int
