"""Modelos de dominio de la asistencia en sitio (HU06).

HU06 no agrega un ramo nuevo: trabaja con los ramos actuales (ver `RamoPoliza`). Solo VIAJE y
PROTECCION_DISPOSITIVOS ofrecen servicios de asistencia inicialmente; VIDA y PARAMETRICO no.

Una solicitud de asistencia NO requiere un siniestro previo (HU04/HU20 son independientes).
El cliente nunca envía su propio identificador: el backend lo toma de la sesión.
"""

import math
from datetime import datetime
from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.polizas.dominio.modelos import RamoPoliza


class TipoServicioAsistencia(str, Enum):
    """Catálogo acotado de servicios de asistencia (HU06)."""

    ASISTENCIA_MEDICA = "ASISTENCIA_MEDICA"
    ASISTENCIA_VIAJERO = "ASISTENCIA_VIAJERO"
    DIAGNOSTICO_TECNICO = "DIAGNOSTICO_TECNICO"
    REPARACION_DISPOSITIVO = "REPARACION_DISPOSITIVO"


NOMBRES_SERVICIO: dict[TipoServicioAsistencia, str] = {
    TipoServicioAsistencia.ASISTENCIA_MEDICA: "Atención médica",
    TipoServicioAsistencia.ASISTENCIA_VIAJERO: "Asistencia al viajero",
    TipoServicioAsistencia.DIAGNOSTICO_TECNICO: "Diagnóstico técnico",
    TipoServicioAsistencia.REPARACION_DISPOSITIVO: "Reparación de dispositivo",
}


# Relación explícita ramo -> servicios. No se modifica `RamoPoliza`.
# VIDA y PARAMETRICO no tienen asistencia en HU06: lista vacía, que no es un error.
SERVICIOS_POR_RAMO: dict[RamoPoliza, tuple[TipoServicioAsistencia, ...]] = {
    RamoPoliza.VIAJE: (
        TipoServicioAsistencia.ASISTENCIA_MEDICA,
        TipoServicioAsistencia.ASISTENCIA_VIAJERO,
    ),
    RamoPoliza.PROTECCION_DISPOSITIVOS: (
        TipoServicioAsistencia.DIAGNOSTICO_TECNICO,
        TipoServicioAsistencia.REPARACION_DISPOSITIVO,
    ),
    RamoPoliza.VIDA: (),
    RamoPoliza.PARAMETRICO: (),
}


def servicios_del_ramo(ramo: RamoPoliza) -> tuple[TipoServicioAsistencia, ...]:
    return SERVICIOS_POR_RAMO.get(ramo, ())


def ramo_ofrece_servicio(ramo: RamoPoliza, servicio: TipoServicioAsistencia) -> bool:
    return servicio in servicios_del_ramo(ramo)


class EstadoAsistencia(str, Enum):
    """Ciclo de vida acotado de la asistencia (HU06). No se agregan estados sin flujo real."""

    SOLICITADA = "SOLICITADA"
    ACEPTADA = "ACEPTADA"
    CANCELADA = "CANCELADA"


# Tiempo estimado de llegada (ETA) en minutos. Es opcional: NULL cuando aún no está disponible.
ETA_MINIMO_MINUTOS = 1
ETA_MAXIMO_MINUTOS = 1440  # 24 horas


class Prestador(BaseModel):
    """Prestador de servicios de asistencia. Son datos de Solventa, precargados por seed (HU06)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    prestador_id: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=200)
    direccion: str = Field(min_length=1, max_length=300)
    telefono: str | None = Field(default=None, max_length=30)
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    servicios: list[TipoServicioAsistencia] = Field(min_length=1)
    activo: bool = True

    def ofrece(self, servicio: TipoServicioAsistencia) -> bool:
        return servicio in self.servicios


class SolicitudAsistencia(BaseModel):
    """Asistencia solicitada por un cliente. `siniestro_id` no es obligatorio (NULL es válido)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    asistencia_id: str = Field(min_length=1, max_length=50)
    cliente_id: str = Field(min_length=1, max_length=50)
    poliza_id: str = Field(min_length=1, max_length=50)
    prestador_id: str = Field(min_length=1, max_length=50)
    servicio: TipoServicioAsistencia
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    observaciones: str | None = Field(default=None, max_length=500)
    estado: EstadoAsistencia = EstadoAsistencia.SOLICITADA
    creada_en: AwareDatetime
    # Seguimiento operativo (HU06 ampliación): se llenan cuando Operaciones acepta la solicitud.
    # El ETA es opcional incluso estando ACEPTADA: NULL significa "aún no disponible".
    aceptada_en: AwareDatetime | None = None
    tiempo_estimado_llegada_minutos: int | None = Field(
        default=None, ge=ETA_MINIMO_MINUTOS, le=ETA_MAXIMO_MINUTOS
    )
    cancelada_en: AwareDatetime | None = None

    def es_cancelable(self) -> bool:
        return self.estado is EstadoAsistencia.SOLICITADA


class NuevaAsistencia(BaseModel):
    """Cuerpo del POST de creación. El cliente nunca envía cliente_id, estado ni fechas."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    poliza_id: str = Field(min_length=1, max_length=50)
    prestador_id: str = Field(min_length=1, max_length=50)
    servicio: TipoServicioAsistencia
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    observaciones: str | None = Field(default=None, max_length=500)


class AceptacionAsistencia(BaseModel):
    """Cuerpo del POST de aceptación (rol Operaciones). El ETA es opcional: `{}` es válido."""

    model_config = ConfigDict(extra="forbid")

    tiempo_estimado_llegada_minutos: int | None = Field(
        default=None, ge=ETA_MINIMO_MINUTOS, le=ETA_MAXIMO_MINUTOS
    )


class SeguimientoAsistencia(BaseModel):
    """Cuerpo del PATCH de seguimiento (rol Operaciones): actualiza el ETA de una ACEPTADA."""

    model_config = ConfigDict(extra="forbid")

    tiempo_estimado_llegada_minutos: int | None = Field(
        default=None, ge=ETA_MINIMO_MINUTOS, le=ETA_MAXIMO_MINUTOS
    )


# Radio de búsqueda de prestadores (km).
RADIO_KM_POR_DEFECTO = 25.0
RADIO_KM_MINIMO = 1.0
RADIO_KM_MAXIMO = 100.0

# Radio medio de la Tierra en kilómetros (fórmula de Haversine).
_RADIO_TIERRA_KM = 6371.0088


def distancia_km(
    latitud_origen: float,
    longitud_origen: float,
    latitud_destino: float,
    longitud_destino: float,
) -> float:
    """Distancia en kilómetros entre dos puntos por la fórmula de Haversine.

    Función pura y determinista: no depende de PostGIS ni de servicios externos (HU06).
    Devuelve 0.0 cuando los puntos coinciden.
    """
    lat1 = math.radians(latitud_origen)
    lat2 = math.radians(latitud_destino)
    d_lat = math.radians(latitud_destino - latitud_origen)
    d_lon = math.radians(longitud_destino - longitud_origen)
    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    c = 2 * math.asin(min(1.0, math.sqrt(a)))
    return _RADIO_TIERRA_KM * c


def ahora_utc() -> datetime:
    from datetime import UTC

    return datetime.now(UTC)
