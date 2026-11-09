"""Persistencia de las cancelaciones de póliza (HU22 / BPM-35).

`registrar` guarda la cancelación y la póliza ya cancelada en una sola transacción: no puede
quedar una cancelación sin aplicar ni una póliza cancelada sin su registro. Si la póliza ya
tenía una cancelación (o la clave de idempotencia ya se usó), se revierte y se informa
`CancelacionConcurrente`.
"""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.polizas.dominio.cancelacion import Cancelacion
from app.polizas.dominio.modelos import Poliza
from app.polizas.modelos_db import CancelacionDB, PolizaDB
from app.polizas.repositorio import (
    RepositorioPolizasEnMemoria,
    con_zona_horaria,
    poliza_a_persistencia,
)


class CancelacionConcurrente(Exception):
    """La póliza ya se había cancelado, o se cancelaba al mismo tiempo."""


class RepositorioCancelaciones(Protocol):
    def registrar(self, cancelacion: Cancelacion, poliza: Poliza) -> None: ...

    def por_poliza(self, poliza_id: str) -> Cancelacion | None: ...

    def por_clave(self, poliza_id: str, clave_idempotencia: str) -> Cancelacion | None: ...


class RepositorioCancelacionesEnMemoria:
    def __init__(self, polizas: RepositorioPolizasEnMemoria):
        self._polizas = polizas
        self._por_poliza: dict[str, Cancelacion] = {}

    def registrar(self, cancelacion: Cancelacion, poliza: Poliza) -> None:
        if cancelacion.poliza_id in self._por_poliza:
            raise CancelacionConcurrente(cancelacion.poliza_id)
        self._por_poliza[cancelacion.poliza_id] = cancelacion.model_copy(deep=True)
        self._polizas.guardar(poliza)

    def por_poliza(self, poliza_id: str) -> Cancelacion | None:
        cancelacion = self._por_poliza.get(poliza_id)
        return cancelacion.model_copy(deep=True) if cancelacion is not None else None

    def por_clave(self, poliza_id: str, clave_idempotencia: str) -> Cancelacion | None:
        cancelacion = self._por_poliza.get(poliza_id)
        if cancelacion is not None and cancelacion.clave_idempotencia == clave_idempotencia:
            return cancelacion.model_copy(deep=True)
        return None


class RepositorioCancelacionesPostgres:
    def __init__(self, db: Session):
        self._db = db

    def registrar(self, cancelacion: Cancelacion, poliza: Poliza) -> None:
        try:
            self._db.add(CancelacionDB(**_a_persistencia(cancelacion)))
            persistida = self._db.get(PolizaDB, poliza.poliza_id)
            datos = poliza_a_persistencia(poliza)
            if persistida is None:
                self._db.add(PolizaDB(**datos))
            else:
                for campo, valor in datos.items():
                    setattr(persistida, campo, valor)
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            raise CancelacionConcurrente(cancelacion.poliza_id) from None

    def por_poliza(self, poliza_id: str) -> Cancelacion | None:
        sentencia = select(CancelacionDB).where(CancelacionDB.poliza_id == poliza_id)
        registro = self._db.scalars(sentencia).first()
        return _a_dominio(registro) if registro is not None else None

    def por_clave(self, poliza_id: str, clave_idempotencia: str) -> Cancelacion | None:
        sentencia = select(CancelacionDB).where(
            CancelacionDB.poliza_id == poliza_id,
            CancelacionDB.clave_idempotencia == clave_idempotencia,
        )
        registro = self._db.scalars(sentencia).first()
        return _a_dominio(registro) if registro is not None else None


def _a_persistencia(cancelacion: Cancelacion) -> dict[str, object]:
    datos = cancelacion.model_dump()
    datos.update(
        motivo=cancelacion.motivo.value,
        estado_devolucion=cancelacion.estado_devolucion.value,
    )
    return datos


def _a_dominio(registro: CancelacionDB) -> Cancelacion:
    columnas = {c.name for c in CancelacionDB.__table__.columns}
    datos = {nombre: getattr(registro, nombre) for nombre in columnas}
    datos["creado_en"] = con_zona_horaria(registro.creado_en)
    return Cancelacion.model_validate(datos)
