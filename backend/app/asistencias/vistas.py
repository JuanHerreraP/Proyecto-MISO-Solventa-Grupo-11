"""Modelos de respuesta de la asistencia en sitio (HU06)."""

from datetime import datetime

from pydantic import BaseModel

from app.asistencias.modelos import (
    NOMBRES_SERVICIO,
    EstadoAsistencia,
    Prestador,
    SolicitudAsistencia,
    TipoServicioAsistencia,
    servicios_del_ramo,
)
from app.polizas.dominio.modelos import NOMBRES_RAMO, RamoPoliza


class ServicioDisponible(BaseModel):
    codigo: TipoServicioAsistencia
    nombre: str


class ServiciosPoliza(BaseModel):
    poliza_id: str
    ramo: RamoPoliza
    servicios: list[ServicioDisponible]


class Ubicacion(BaseModel):
    latitud: float
    longitud: float


class PrestadorCercano(BaseModel):
    prestador_id: str
    nombre: str
    tipo_servicio: TipoServicioAsistencia
    direccion: str
    telefono: str | None
    latitud: float
    longitud: float
    distancia_km: float


class PrestadoresCercanos(BaseModel):
    poliza_id: str
    servicio: TipoServicioAsistencia
    ubicacion: Ubicacion
    prestadores: list[PrestadorCercano]


class PrestadorResumen(BaseModel):
    prestador_id: str
    nombre: str
    telefono: str | None


class AsistenciaCreada(BaseModel):
    asistencia_id: str
    poliza_id: str
    prestador: PrestadorResumen
    servicio: TipoServicioAsistencia
    estado: EstadoAsistencia
    ubicacion: Ubicacion
    observaciones: str | None
    creada_en: datetime
    # Seguimiento (HU06 ampliación): NULL hasta que Operaciones acepte / registre el ETA.
    aceptada_en: datetime | None = None
    tiempo_estimado_llegada_minutos: int | None = None
    cancelada_en: datetime | None = None


class AsistenciaOperaciones(BaseModel):
    """Vista de seguimiento para el rol Operaciones. Incluye el cliente y el número de póliza."""

    asistencia_id: str
    cliente_id: str
    poliza_id: str
    numero_poliza: str | None = None
    servicio: TipoServicioAsistencia
    prestador: PrestadorResumen
    estado: EstadoAsistencia
    ubicacion: Ubicacion
    observaciones: str | None
    creada_en: datetime
    aceptada_en: datetime | None = None
    tiempo_estimado_llegada_minutos: int | None = None
    cancelada_en: datetime | None = None


def a_servicios_poliza(poliza_id: str, ramo: RamoPoliza) -> ServiciosPoliza:
    return ServiciosPoliza(
        poliza_id=poliza_id,
        ramo=ramo,
        servicios=[
            ServicioDisponible(codigo=servicio, nombre=NOMBRES_SERVICIO[servicio])
            for servicio in servicios_del_ramo(ramo)
        ],
    )


def a_prestador_cercano(
    prestador: Prestador, servicio: TipoServicioAsistencia, distancia: float
) -> PrestadorCercano:
    return PrestadorCercano(
        prestador_id=prestador.prestador_id,
        nombre=prestador.nombre,
        tipo_servicio=servicio,
        direccion=prestador.direccion,
        telefono=prestador.telefono,
        latitud=prestador.latitud,
        longitud=prestador.longitud,
        distancia_km=round(distancia, 2),
    )


def a_asistencia_creada(asistencia: SolicitudAsistencia, prestador: Prestador) -> AsistenciaCreada:
    return AsistenciaCreada(
        asistencia_id=asistencia.asistencia_id,
        poliza_id=asistencia.poliza_id,
        prestador=PrestadorResumen(
            prestador_id=prestador.prestador_id,
            nombre=prestador.nombre,
            telefono=prestador.telefono,
        ),
        servicio=asistencia.servicio,
        estado=asistencia.estado,
        ubicacion=Ubicacion(latitud=asistencia.latitud, longitud=asistencia.longitud),
        observaciones=asistencia.observaciones,
        creada_en=asistencia.creada_en,
        aceptada_en=asistencia.aceptada_en,
        tiempo_estimado_llegada_minutos=asistencia.tiempo_estimado_llegada_minutos,
        cancelada_en=asistencia.cancelada_en,
    )


def a_asistencia_operaciones(
    asistencia: SolicitudAsistencia, prestador: Prestador, numero_poliza: str | None
) -> AsistenciaOperaciones:
    return AsistenciaOperaciones(
        asistencia_id=asistencia.asistencia_id,
        cliente_id=asistencia.cliente_id,
        poliza_id=asistencia.poliza_id,
        numero_poliza=numero_poliza,
        servicio=asistencia.servicio,
        prestador=PrestadorResumen(
            prestador_id=prestador.prestador_id,
            nombre=prestador.nombre,
            telefono=prestador.telefono,
        ),
        estado=asistencia.estado,
        ubicacion=Ubicacion(latitud=asistencia.latitud, longitud=asistencia.longitud),
        observaciones=asistencia.observaciones,
        creada_en=asistencia.creada_en,
        aceptada_en=asistencia.aceptada_en,
        tiempo_estimado_llegada_minutos=asistencia.tiempo_estimado_llegada_minutos,
        cancelada_en=asistencia.cancelada_en,
    )


__all__ = [
    "NOMBRES_RAMO",
    "AsistenciaCreada",
    "AsistenciaOperaciones",
    "PrestadorCercano",
    "PrestadorResumen",
    "PrestadoresCercanos",
    "ServicioDisponible",
    "ServiciosPoliza",
    "Ubicacion",
    "a_asistencia_creada",
    "a_asistencia_operaciones",
    "a_prestador_cercano",
    "a_servicios_poliza",
]
