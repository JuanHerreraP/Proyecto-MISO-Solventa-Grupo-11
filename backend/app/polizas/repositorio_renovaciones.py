"""Persistencia de las renovaciones de póliza (HU22 / BPM-35).

`aplicar` guarda la renovación como aplicada y la póliza con su nuevo periodo en una sola
transacción: no puede quedar una renovación aplicada sin su póliza actualizada, ni al revés.
Aplicar dos veces la misma renovación (confirmación del pago y consulta del cliente a la vez)
es inocuo: la segunda no cambia nada.
"""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.polizas.dominio.modelos import Poliza
from app.polizas.dominio.renovacion import EstadoRenovacion, Renovacion
from app.polizas.modelos_db import PolizaDB, RenovacionDB
from app.polizas.repositorio import (
    RepositorioPolizasEnMemoria,
    con_zona_horaria,
    poliza_a_persistencia,
)


class RenovacionConcurrente(Exception):
    """La renovación del periodo ya existe, o se creaba al mismo tiempo."""


class RepositorioRenovaciones(Protocol):
    def crear(self, renovacion: Renovacion) -> None: ...

    def reemplazar_pendiente(self, renovacion: Renovacion) -> None: ...

    def marcar_no_aplicada(self, renovacion: Renovacion) -> None: ...

    def aplicar(self, renovacion: Renovacion, poliza: Poliza) -> bool: ...

    def obtener(self, renovacion_id: str) -> Renovacion | None: ...

    def por_cotizacion(self, cotizacion_id: str) -> Renovacion | None: ...

    def por_poliza(self, poliza_id: str) -> list[Renovacion]: ...

    def por_clave(self, poliza_id: str, clave_idempotencia: str) -> Renovacion | None: ...


def _recientes_primero(renovaciones: list[Renovacion]) -> list[Renovacion]:
    return sorted(renovaciones, key=lambda r: r.creado_en, reverse=True)


class RepositorioRenovacionesEnMemoria:
    def __init__(self, polizas: RepositorioPolizasEnMemoria):
        self._polizas = polizas
        self._por_id: dict[str, Renovacion] = {}

    def crear(self, renovacion: Renovacion) -> None:
        if renovacion.renovacion_id in self._por_id:
            raise RenovacionConcurrente(renovacion.renovacion_id)
        self._por_id[renovacion.renovacion_id] = renovacion.model_copy(deep=True)

    def reemplazar_pendiente(self, renovacion: Renovacion) -> None:
        actual = self._por_id.get(renovacion.renovacion_id)
        if actual is None or actual.estado is EstadoRenovacion.APLICADA:
            raise RenovacionConcurrente(renovacion.renovacion_id)
        self._por_id[renovacion.renovacion_id] = renovacion.model_copy(deep=True)

    def marcar_no_aplicada(self, renovacion: Renovacion) -> None:
        actual = self._por_id.get(renovacion.renovacion_id)
        if actual is not None and actual.estado is not EstadoRenovacion.APLICADA:
            self._por_id[renovacion.renovacion_id] = renovacion.model_copy(deep=True)

    def aplicar(self, renovacion: Renovacion, poliza: Poliza) -> bool:
        actual = self._por_id.get(renovacion.renovacion_id)
        if actual is None or actual.estado is EstadoRenovacion.APLICADA:
            return False
        self._por_id[renovacion.renovacion_id] = renovacion.model_copy(deep=True)
        self._polizas.guardar(poliza)
        return True

    def obtener(self, renovacion_id: str) -> Renovacion | None:
        renovacion = self._por_id.get(renovacion_id)
        return renovacion.model_copy(deep=True) if renovacion is not None else None

    def por_cotizacion(self, cotizacion_id: str) -> Renovacion | None:
        for renovacion in self._por_id.values():
            if renovacion.cotizacion_id == cotizacion_id:
                return renovacion.model_copy(deep=True)
        return None

    def por_poliza(self, poliza_id: str) -> list[Renovacion]:
        return _recientes_primero(
            [r.model_copy(deep=True) for r in self._por_id.values() if r.poliza_id == poliza_id]
        )

    def por_clave(self, poliza_id: str, clave_idempotencia: str) -> Renovacion | None:
        for renovacion in self._por_id.values():
            if (
                renovacion.poliza_id == poliza_id
                and renovacion.clave_idempotencia == clave_idempotencia
            ):
                return renovacion.model_copy(deep=True)
        return None


class RepositorioRenovacionesPostgres:
    def __init__(self, db: Session):
        self._db = db

    def crear(self, renovacion: Renovacion) -> None:
        try:
            self._db.add(RenovacionDB(**_a_persistencia(renovacion)))
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            raise RenovacionConcurrente(renovacion.renovacion_id) from None

    def reemplazar_pendiente(self, renovacion: Renovacion) -> None:
        try:
            registro = self._db.get(RenovacionDB, renovacion.renovacion_id)
            if registro is None or registro.estado == EstadoRenovacion.APLICADA.value:
                raise RenovacionConcurrente(renovacion.renovacion_id)
            for campo, valor in _a_persistencia(renovacion).items():
                setattr(registro, campo, valor)
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            raise RenovacionConcurrente(renovacion.renovacion_id) from None

    def marcar_no_aplicada(self, renovacion: Renovacion) -> None:
        registro = self._db.get(RenovacionDB, renovacion.renovacion_id)
        if registro is None or registro.estado == EstadoRenovacion.APLICADA.value:
            return
        for campo, valor in _a_persistencia(renovacion).items():
            setattr(registro, campo, valor)
        self._db.commit()

    def aplicar(self, renovacion: Renovacion, poliza: Poliza) -> bool:
        registro = self._db.get(RenovacionDB, renovacion.renovacion_id)
        if registro is None or registro.estado == EstadoRenovacion.APLICADA.value:
            return False
        for campo, valor in _a_persistencia(renovacion).items():
            setattr(registro, campo, valor)
        persistida = self._db.get(PolizaDB, poliza.poliza_id)
        datos = poliza_a_persistencia(poliza)
        if persistida is None:
            self._db.add(PolizaDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(persistida, campo, valor)
        self._db.commit()
        return True

    def obtener(self, renovacion_id: str) -> Renovacion | None:
        registro = self._db.get(RenovacionDB, renovacion_id)
        return _a_dominio(registro) if registro is not None else None

    def por_cotizacion(self, cotizacion_id: str) -> Renovacion | None:
        sentencia = select(RenovacionDB).where(RenovacionDB.cotizacion_id == cotizacion_id)
        registro = self._db.scalars(sentencia).first()
        return _a_dominio(registro) if registro is not None else None

    def por_poliza(self, poliza_id: str) -> list[Renovacion]:
        sentencia = (
            select(RenovacionDB)
            .where(RenovacionDB.poliza_id == poliza_id)
            .order_by(RenovacionDB.creado_en.desc())
        )
        return [_a_dominio(r) for r in self._db.scalars(sentencia)]

    def por_clave(self, poliza_id: str, clave_idempotencia: str) -> Renovacion | None:
        sentencia = select(RenovacionDB).where(
            RenovacionDB.poliza_id == poliza_id,
            RenovacionDB.clave_idempotencia == clave_idempotencia,
        )
        registro = self._db.scalars(sentencia).first()
        return _a_dominio(registro) if registro is not None else None


def _a_persistencia(renovacion: Renovacion) -> dict[str, object]:
    datos = renovacion.model_dump()
    datos["estado"] = renovacion.estado.value
    return datos


def _a_dominio(registro: RenovacionDB) -> Renovacion:
    columnas = {c.name for c in RenovacionDB.__table__.columns}
    datos = {nombre: getattr(registro, nombre) for nombre in columnas}
    for campo in ("vigente_hasta", "creado_en", "aplicada_en"):
        datos[campo] = con_zona_horaria(datos[campo]) if datos[campo] is not None else None
    return Renovacion.model_validate(datos)
