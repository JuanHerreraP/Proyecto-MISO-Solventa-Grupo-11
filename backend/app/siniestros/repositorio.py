"""Persistencia de siniestros (HU20)."""

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.siniestros.modelos import EstadoSiniestro, Siniestro
from app.siniestros.modelos_db import SiniestroDB


class RepositorioSiniestros(Protocol):
    def guardar(self, siniestro: Siniestro) -> None: ...

    def obtener(self, siniestro_id: str) -> Siniestro | None: ...

    def obtener_por_evento(self, evento_id: str) -> Siniestro | None: ...

    def listar_por_cliente(self, cliente_id: str) -> list[Siniestro]: ...

    def listar_por_poliza(self, poliza_id: str) -> list[Siniestro]:
        """Siniestros de una póliza, del más reciente al más antiguo."""
        ...

    def listar(self, estado: EstadoSiniestro | None = None, limite: int = 200) -> list[Siniestro]:
        """Todos los siniestros (bandeja de Operaciones), del más reciente al más antiguo."""
        ...


class RepositorioSiniestrosEnMemoria:
    def __init__(self):
        self._por_id: dict[str, Siniestro] = {}

    def guardar(self, siniestro: Siniestro) -> None:
        self._por_id[siniestro.siniestro_id] = siniestro.model_copy(deep=True)

    def obtener(self, siniestro_id: str) -> Siniestro | None:
        siniestro = self._por_id.get(siniestro_id)
        return siniestro.model_copy(deep=True) if siniestro is not None else None

    def obtener_por_evento(self, evento_id: str) -> Siniestro | None:
        for siniestro in self._por_id.values():
            if siniestro.evento_id == evento_id:
                return siniestro.model_copy(deep=True)
        return None

    def listar_por_cliente(self, cliente_id: str) -> list[Siniestro]:
        propios = [s for s in self._por_id.values() if s.cliente_id == cliente_id]
        propios.sort(key=lambda s: s.registrado_en, reverse=True)
        return [s.model_copy(deep=True) for s in propios]

    def listar_por_poliza(self, poliza_id: str) -> list[Siniestro]:
        de_la_poliza = [s for s in self._por_id.values() if s.poliza_id == poliza_id]
        de_la_poliza.sort(key=lambda s: s.registrado_en, reverse=True)
        return [s.model_copy(deep=True) for s in de_la_poliza]

    def listar(self, estado: EstadoSiniestro | None = None, limite: int = 200) -> list[Siniestro]:
        todos = [s for s in self._por_id.values() if estado is None or s.estado is estado]
        todos.sort(key=lambda s: s.registrado_en, reverse=True)
        return [s.model_copy(deep=True) for s in todos[:limite]]


class RepositorioSiniestrosPostgres:
    def __init__(self, db: Session):
        self._db = db

    def guardar(self, siniestro: Siniestro) -> None:
        datos = _a_persistencia(siniestro)
        persistido = self._db.get(SiniestroDB, siniestro.siniestro_id)
        if persistido is None:
            self._db.add(SiniestroDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(persistido, campo, valor)
        self._db.commit()

    def obtener(self, siniestro_id: str) -> Siniestro | None:
        registro = self._db.get(SiniestroDB, siniestro_id)
        return _a_dominio(registro) if registro is not None else None

    def obtener_por_evento(self, evento_id: str) -> Siniestro | None:
        sentencia = select(SiniestroDB).where(SiniestroDB.evento_id == evento_id)
        registro = self._db.scalars(sentencia).first()
        return _a_dominio(registro) if registro is not None else None

    def listar_por_cliente(self, cliente_id: str) -> list[Siniestro]:
        sentencia = (
            select(SiniestroDB)
            .where(SiniestroDB.cliente_id == cliente_id)
            .order_by(SiniestroDB.registrado_en.desc())
        )
        return [_a_dominio(fila) for fila in self._db.scalars(sentencia).all()]

    def listar_por_poliza(self, poliza_id: str) -> list[Siniestro]:
        sentencia = (
            select(SiniestroDB)
            .where(SiniestroDB.poliza_id == poliza_id)
            .order_by(SiniestroDB.registrado_en.desc())
        )
        return [_a_dominio(fila) for fila in self._db.scalars(sentencia).all()]

    def listar(self, estado: EstadoSiniestro | None = None, limite: int = 200) -> list[Siniestro]:
        sentencia = select(SiniestroDB).order_by(SiniestroDB.registrado_en.desc()).limit(limite)
        if estado is not None:
            sentencia = sentencia.where(SiniestroDB.estado == estado.value)
        return [_a_dominio(fila) for fila in self._db.scalars(sentencia).all()]


def _a_persistencia(siniestro: Siniestro) -> dict[str, object]:
    datos = siniestro.model_dump()
    datos.update(origen=siniestro.origen.value, estado=siniestro.estado.value)
    return datos


def _a_dominio(registro: SiniestroDB) -> Siniestro:
    return Siniestro.model_validate(
        {
            "siniestro_id": registro.siniestro_id,
            "cliente_id": registro.cliente_id,
            "poliza_id": registro.poliza_id,
            "origen": registro.origen,
            "estado": registro.estado,
            "evento_id": registro.evento_id,
            "fecha_evento": registro.fecha_evento,
            "hora_evento": registro.hora_evento,
            "lugar": registro.lugar,
            "descripcion": registro.descripcion,
            "estimacion_danos": registro.estimacion_danos,
            "moneda": registro.moneda,
            "registrado_por": registro.registrado_por,
            "registrado_en": _con_zona(registro.registrado_en),
            "monto_aprobado": registro.monto_aprobado,
            "evaluado_por": registro.evaluado_por,
            "evaluado_en": _con_zona(registro.evaluado_en),
            "motivo_rechazo": registro.motivo_rechazo,
        }
    )


def _con_zona(fecha: datetime | None) -> datetime | None:
    if fecha is None:
        return None
    return fecha.replace(tzinfo=UTC) if fecha.tzinfo is None else fecha
