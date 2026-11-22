"""Persistencia de prestadores y asistencias (HU06)."""

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.asistencias.modelos import (
    EstadoAsistencia,
    Prestador,
    SolicitudAsistencia,
    TipoServicioAsistencia,
)
from app.asistencias.modelos_db import AsistenciaDB, PrestadorDB, PrestadorServicioDB


class RepositorioPrestadores(Protocol):
    def guardar(self, prestador: Prestador) -> None: ...

    def obtener(self, prestador_id: str) -> Prestador | None: ...

    def listar_activos(self) -> list[Prestador]:
        """Prestadores activos (los inactivos no se ofrecen al cliente)."""
        ...


class RepositorioAsistencias(Protocol):
    def guardar(self, asistencia: SolicitudAsistencia) -> None: ...

    def obtener(self, asistencia_id: str) -> SolicitudAsistencia | None: ...

    def listar_por_cliente(self, cliente_id: str) -> list[SolicitudAsistencia]:
        """Asistencias del cliente, de la más reciente a la más antigua."""
        ...

    def listar(
        self,
        estado: EstadoAsistencia | None = None,
        poliza_id: str | None = None,
        prestador_id: str | None = None,
        limite: int = 200,
    ) -> list[SolicitudAsistencia]:
        """Todas las asistencias (bandeja de Operaciones), de la más reciente a la más antigua."""
        ...


class RepositorioPrestadoresEnMemoria:
    def __init__(self) -> None:
        self._por_id: dict[str, Prestador] = {}

    def guardar(self, prestador: Prestador) -> None:
        self._por_id[prestador.prestador_id] = prestador.model_copy(deep=True)

    def obtener(self, prestador_id: str) -> Prestador | None:
        prestador = self._por_id.get(prestador_id)
        return prestador.model_copy(deep=True) if prestador is not None else None

    def listar_activos(self) -> list[Prestador]:
        return [p.model_copy(deep=True) for p in self._por_id.values() if p.activo]


class RepositorioAsistenciasEnMemoria:
    def __init__(self) -> None:
        self._por_id: dict[str, SolicitudAsistencia] = {}

    def guardar(self, asistencia: SolicitudAsistencia) -> None:
        self._por_id[asistencia.asistencia_id] = asistencia.model_copy(deep=True)

    def obtener(self, asistencia_id: str) -> SolicitudAsistencia | None:
        asistencia = self._por_id.get(asistencia_id)
        return asistencia.model_copy(deep=True) if asistencia is not None else None

    def listar_por_cliente(self, cliente_id: str) -> list[SolicitudAsistencia]:
        propias = [a for a in self._por_id.values() if a.cliente_id == cliente_id]
        propias.sort(key=lambda a: a.creada_en, reverse=True)
        return [a.model_copy(deep=True) for a in propias]

    def listar(
        self,
        estado: EstadoAsistencia | None = None,
        poliza_id: str | None = None,
        prestador_id: str | None = None,
        limite: int = 200,
    ) -> list[SolicitudAsistencia]:
        filtradas = [
            a
            for a in self._por_id.values()
            if (estado is None or a.estado is estado)
            and (poliza_id is None or a.poliza_id == poliza_id)
            and (prestador_id is None or a.prestador_id == prestador_id)
        ]
        filtradas.sort(key=lambda a: a.creada_en, reverse=True)
        return [a.model_copy(deep=True) for a in filtradas[:limite]]


class RepositorioPrestadoresPostgres:
    def __init__(self, db: Session) -> None:
        self._db = db

    def guardar(self, prestador: Prestador) -> None:
        persistido = self._db.get(PrestadorDB, prestador.prestador_id)
        datos = {
            "prestador_id": prestador.prestador_id,
            "nombre": prestador.nombre,
            "direccion": prestador.direccion,
            "telefono": prestador.telefono,
            "latitud": prestador.latitud,
            "longitud": prestador.longitud,
            "activo": prestador.activo,
        }
        if persistido is None:
            self._db.add(PrestadorDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(persistido, campo, valor)
        # Reescribe los servicios para que el guardado sea idempotente.
        existentes = self._db.scalars(
            select(PrestadorServicioDB).where(
                PrestadorServicioDB.prestador_id == prestador.prestador_id
            )
        ).all()
        for fila in existentes:
            self._db.delete(fila)
        for servicio in dict.fromkeys(prestador.servicios):
            self._db.add(
                PrestadorServicioDB(prestador_id=prestador.prestador_id, servicio=servicio.value)
            )
        self._db.commit()

    def obtener(self, prestador_id: str) -> Prestador | None:
        registro = self._db.get(PrestadorDB, prestador_id)
        return _prestador_a_dominio(registro, self._servicios(prestador_id)) if registro else None

    def listar_activos(self) -> list[Prestador]:
        registros = self._db.scalars(select(PrestadorDB).where(PrestadorDB.activo.is_(True))).all()
        return [
            _prestador_a_dominio(registro, self._servicios(registro.prestador_id))
            for registro in registros
        ]

    def _servicios(self, prestador_id: str) -> list[TipoServicioAsistencia]:
        filas = self._db.scalars(
            select(PrestadorServicioDB).where(PrestadorServicioDB.prestador_id == prestador_id)
        ).all()
        servicios: list[TipoServicioAsistencia] = []
        for fila in filas:
            try:
                servicios.append(TipoServicioAsistencia(fila.servicio))
            except ValueError:
                # Un servicio desconocido en la base no debe romper la consulta.
                continue
        return servicios


class RepositorioAsistenciasPostgres:
    def __init__(self, db: Session) -> None:
        self._db = db

    def guardar(self, asistencia: SolicitudAsistencia) -> None:
        datos = {
            "asistencia_id": asistencia.asistencia_id,
            "cliente_id": asistencia.cliente_id,
            "poliza_id": asistencia.poliza_id,
            "prestador_id": asistencia.prestador_id,
            "servicio": asistencia.servicio.value,
            "latitud": asistencia.latitud,
            "longitud": asistencia.longitud,
            "observaciones": asistencia.observaciones,
            "estado": asistencia.estado.value,
            "creada_en": asistencia.creada_en,
            "cancelada_en": asistencia.cancelada_en,
            "aceptada_en": asistencia.aceptada_en,
            "tiempo_estimado_llegada_minutos": asistencia.tiempo_estimado_llegada_minutos,
        }
        persistida = self._db.get(AsistenciaDB, asistencia.asistencia_id)
        if persistida is None:
            self._db.add(AsistenciaDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(persistida, campo, valor)
        self._db.commit()

    def obtener(self, asistencia_id: str) -> SolicitudAsistencia | None:
        registro = self._db.get(AsistenciaDB, asistencia_id)
        return _asistencia_a_dominio(registro) if registro is not None else None

    def listar_por_cliente(self, cliente_id: str) -> list[SolicitudAsistencia]:
        sentencia = (
            select(AsistenciaDB)
            .where(AsistenciaDB.cliente_id == cliente_id)
            .order_by(AsistenciaDB.creada_en.desc())
        )
        return [_asistencia_a_dominio(fila) for fila in self._db.scalars(sentencia).all()]

    def listar(
        self,
        estado: EstadoAsistencia | None = None,
        poliza_id: str | None = None,
        prestador_id: str | None = None,
        limite: int = 200,
    ) -> list[SolicitudAsistencia]:
        sentencia = select(AsistenciaDB).order_by(AsistenciaDB.creada_en.desc()).limit(limite)
        if estado is not None:
            sentencia = sentencia.where(AsistenciaDB.estado == estado.value)
        if poliza_id is not None:
            sentencia = sentencia.where(AsistenciaDB.poliza_id == poliza_id)
        if prestador_id is not None:
            sentencia = sentencia.where(AsistenciaDB.prestador_id == prestador_id)
        return [_asistencia_a_dominio(fila) for fila in self._db.scalars(sentencia).all()]


def _prestador_a_dominio(
    registro: PrestadorDB, servicios: list[TipoServicioAsistencia]
) -> Prestador:
    return Prestador(
        prestador_id=registro.prestador_id,
        nombre=registro.nombre,
        direccion=registro.direccion,
        telefono=registro.telefono,
        latitud=registro.latitud,
        longitud=registro.longitud,
        servicios=servicios,
        activo=registro.activo,
    )


def _asistencia_a_dominio(registro: AsistenciaDB) -> SolicitudAsistencia:
    return SolicitudAsistencia(
        asistencia_id=registro.asistencia_id,
        cliente_id=registro.cliente_id,
        poliza_id=registro.poliza_id,
        prestador_id=registro.prestador_id,
        servicio=TipoServicioAsistencia(registro.servicio),
        latitud=registro.latitud,
        longitud=registro.longitud,
        observaciones=registro.observaciones,
        estado=EstadoAsistencia(registro.estado),
        creada_en=_con_zona(registro.creada_en),
        cancelada_en=_con_zona(registro.cancelada_en),
        aceptada_en=_con_zona(registro.aceptada_en),
        tiempo_estimado_llegada_minutos=registro.tiempo_estimado_llegada_minutos,
    )


def _con_zona(fecha: datetime | None) -> datetime | None:
    if fecha is None:
        return None
    return fecha.replace(tzinfo=UTC) if fecha.tzinfo is None else fecha
