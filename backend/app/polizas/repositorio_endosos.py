"""Persistencia de los endosos de póliza (HU16 / BPM-68).

`registrar` guarda el endoso y la póliza actualizada en una sola transacción: no puede quedar
un endoso sin aplicar ni una póliza cambiada sin su endoso. Si otra confirmación ya tomó el
mismo número de endoso, la transacción se revierte y se informa `EndosoConcurrente`.
"""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.polizas.dominio.endosos import Endoso
from app.polizas.dominio.modelos import Poliza
from app.polizas.modelos_db import EndosoDB, PolizaDB
from app.polizas.repositorio import (
    RepositorioPolizasEnMemoria,
    con_zona_horaria,
    poliza_a_persistencia,
)


class EndosoConcurrente(Exception):
    """Otra modificación de la misma póliza se confirmó al mismo tiempo."""


class RepositorioEndosos(Protocol):
    def registrar(self, endoso: Endoso, poliza: Poliza) -> None: ...

    def listar_por_poliza(self, poliza_id: str) -> list[Endoso]: ...

    def obtener(self, poliza_id: str, endoso_id: str) -> Endoso | None: ...

    def por_clave(self, poliza_id: str, clave_idempotencia: str) -> Endoso | None: ...


class RepositorioEndososEnMemoria:
    def __init__(self, polizas: RepositorioPolizasEnMemoria):
        self._polizas = polizas
        self._por_id: dict[str, Endoso] = {}

    def registrar(self, endoso: Endoso, poliza: Poliza) -> None:
        for existente in self._por_id.values():
            if existente.poliza_id != endoso.poliza_id:
                continue
            mismo_numero = existente.numero_endoso == endoso.numero_endoso
            misma_clave = (
                endoso.clave_idempotencia is not None
                and existente.clave_idempotencia == endoso.clave_idempotencia
            )
            if mismo_numero or misma_clave:
                raise EndosoConcurrente(endoso.poliza_id)
        self._por_id[endoso.endoso_id] = endoso.model_copy(deep=True)
        self._polizas.guardar(poliza)

    def listar_por_poliza(self, poliza_id: str) -> list[Endoso]:
        endosos = [e for e in self._por_id.values() if e.poliza_id == poliza_id]
        return [e.model_copy(deep=True) for e in sorted(endosos, key=lambda e: e.numero_endoso)]

    def obtener(self, poliza_id: str, endoso_id: str) -> Endoso | None:
        endoso = self._por_id.get(endoso_id)
        if endoso is None or endoso.poliza_id != poliza_id:
            return None
        return endoso.model_copy(deep=True)

    def por_clave(self, poliza_id: str, clave_idempotencia: str) -> Endoso | None:
        for endoso in self._por_id.values():
            if endoso.poliza_id == poliza_id and endoso.clave_idempotencia == clave_idempotencia:
                return endoso.model_copy(deep=True)
        return None


class RepositorioEndososPostgres:
    def __init__(self, db: Session):
        self._db = db

    def registrar(self, endoso: Endoso, poliza: Poliza) -> None:
        try:
            self._db.add(EndosoDB(**_endoso_a_persistencia(endoso)))
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
            raise EndosoConcurrente(endoso.poliza_id) from None

    def listar_por_poliza(self, poliza_id: str) -> list[Endoso]:
        sentencia = (
            select(EndosoDB).where(EndosoDB.poliza_id == poliza_id).order_by(EndosoDB.numero_endoso)
        )
        return [_endoso_a_dominio(r) for r in self._db.scalars(sentencia).all()]

    def obtener(self, poliza_id: str, endoso_id: str) -> Endoso | None:
        registro = self._db.get(EndosoDB, endoso_id)
        if registro is None or registro.poliza_id != poliza_id:
            return None
        return _endoso_a_dominio(registro)

    def por_clave(self, poliza_id: str, clave_idempotencia: str) -> Endoso | None:
        sentencia = select(EndosoDB).where(
            EndosoDB.poliza_id == poliza_id,
            EndosoDB.clave_idempotencia == clave_idempotencia,
        )
        registro = self._db.scalars(sentencia).first()
        return _endoso_a_dominio(registro) if registro is not None else None


def _endoso_a_persistencia(endoso: Endoso) -> dict[str, object]:
    datos = endoso.model_dump()
    datos.update(
        tipo=endoso.tipo.value,
        cambios=[c.model_dump(mode="json") for c in endoso.cambios],
        coberturas_opcionales=[c.model_dump(mode="json") for c in endoso.coberturas_opcionales],
        beneficiarios=[b.model_dump(mode="json") for b in endoso.beneficiarios],
    )
    return datos


def _endoso_a_dominio(registro: EndosoDB) -> Endoso:
    columnas = {c.name for c in EndosoDB.__table__.columns}
    datos = {nombre: getattr(registro, nombre) for nombre in columnas}
    datos["creado_en"] = con_zona_horaria(registro.creado_en)
    return Endoso.model_validate(datos)
