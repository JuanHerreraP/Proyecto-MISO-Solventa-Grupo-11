"""Persistencia de las evidencias de siniestro y de su bitácora de auditoría (HU04 / EC10).

Ninguno de los dos repositorios expone operaciones para modificar o borrar: las evidencias son
inmutables y la bitácora solo crece.
"""

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.siniestros.evidencias import AccesoEvidencia, EvidenciaDuplicada, EvidenciaSiniestro
from app.siniestros.modelos_db import AccesoEvidenciaDB, EvidenciaSiniestroDB


class RepositorioEvidencias(Protocol):
    def guardar(self, evidencia: EvidenciaSiniestro) -> None:
        """Registra una evidencia nueva. EvidenciaDuplicada si su huella ya está en el siniestro."""
        ...

    def obtener(self, evidencia_id: str) -> EvidenciaSiniestro | None: ...

    def obtener_por_huella(self, siniestro_id: str, huella: str) -> EvidenciaSiniestro | None: ...

    def listar_por_siniestro(self, siniestro_id: str) -> list[EvidenciaSiniestro]:
        """Del más antiguo al más reciente, en el orden en que se cargaron."""
        ...

    def contar(self, siniestro_id: str) -> int: ...


class RepositorioAuditoriaEvidencias(Protocol):
    def registrar(self, acceso: AccesoEvidencia) -> None: ...

    def listar_por_siniestro(self, siniestro_id: str) -> list[AccesoEvidencia]:
        """Del más antiguo al más reciente."""
        ...


class RepositorioEvidenciasEnMemoria:
    def __init__(self):
        self._por_id: dict[str, EvidenciaSiniestro] = {}

    def guardar(self, evidencia: EvidenciaSiniestro) -> None:
        if self.obtener_por_huella(evidencia.siniestro_id, evidencia.huella_sha256) is not None:
            raise EvidenciaDuplicada(evidencia.huella_sha256)
        self._por_id[evidencia.evidencia_id] = evidencia.model_copy(deep=True)

    def obtener(self, evidencia_id: str) -> EvidenciaSiniestro | None:
        evidencia = self._por_id.get(evidencia_id)
        return evidencia.model_copy(deep=True) if evidencia is not None else None

    def obtener_por_huella(self, siniestro_id: str, huella: str) -> EvidenciaSiniestro | None:
        for evidencia in self._por_id.values():
            if evidencia.siniestro_id == siniestro_id and evidencia.huella_sha256 == huella:
                return evidencia.model_copy(deep=True)
        return None

    def listar_por_siniestro(self, siniestro_id: str) -> list[EvidenciaSiniestro]:
        propias = [e for e in self._por_id.values() if e.siniestro_id == siniestro_id]
        propias.sort(key=lambda e: e.subida_en)
        return [e.model_copy(deep=True) for e in propias]

    def contar(self, siniestro_id: str) -> int:
        return sum(1 for e in self._por_id.values() if e.siniestro_id == siniestro_id)


class RepositorioAuditoriaEvidenciasEnMemoria:
    def __init__(self):
        self.registros: list[AccesoEvidencia] = []

    def registrar(self, acceso: AccesoEvidencia) -> None:
        self.registros.append(acceso.model_copy())

    def listar_por_siniestro(self, siniestro_id: str) -> list[AccesoEvidencia]:
        return [r.model_copy() for r in self.registros if r.siniestro_id == siniestro_id]


class RepositorioEvidenciasPostgres:
    def __init__(self, db: Session):
        self._db = db

    def guardar(self, evidencia: EvidenciaSiniestro) -> None:
        datos = evidencia.model_dump(exclude={"geoetiquetada"})
        datos.update(tipo=evidencia.tipo.value, clave_almacenamiento=evidencia.clave_almacenamiento)
        self._db.add(EvidenciaSiniestroDB(**datos))
        try:
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            raise EvidenciaDuplicada(evidencia.huella_sha256) from None

    def obtener(self, evidencia_id: str) -> EvidenciaSiniestro | None:
        registro = self._db.get(EvidenciaSiniestroDB, evidencia_id)
        return _evidencia(registro) if registro is not None else None

    def obtener_por_huella(self, siniestro_id: str, huella: str) -> EvidenciaSiniestro | None:
        sentencia = select(EvidenciaSiniestroDB).where(
            EvidenciaSiniestroDB.siniestro_id == siniestro_id,
            EvidenciaSiniestroDB.huella_sha256 == huella,
        )
        registro = self._db.scalars(sentencia).first()
        return _evidencia(registro) if registro is not None else None

    def listar_por_siniestro(self, siniestro_id: str) -> list[EvidenciaSiniestro]:
        sentencia = (
            select(EvidenciaSiniestroDB)
            .where(EvidenciaSiniestroDB.siniestro_id == siniestro_id)
            .order_by(EvidenciaSiniestroDB.subida_en, EvidenciaSiniestroDB.evidencia_id)
        )
        return [_evidencia(fila) for fila in self._db.scalars(sentencia).all()]

    def contar(self, siniestro_id: str) -> int:
        sentencia = select(func.count()).where(EvidenciaSiniestroDB.siniestro_id == siniestro_id)
        return int(self._db.scalar(sentencia) or 0)


class RepositorioAuditoriaEvidenciasPostgres:
    def __init__(self, db: Session):
        self._db = db

    def registrar(self, acceso: AccesoEvidencia) -> None:
        datos = acceso.model_dump()
        datos.update(accion=acceso.accion.value)
        self._db.add(AccesoEvidenciaDB(**datos))
        self._db.commit()

    def listar_por_siniestro(self, siniestro_id: str) -> list[AccesoEvidencia]:
        sentencia = (
            select(AccesoEvidenciaDB)
            .where(AccesoEvidenciaDB.siniestro_id == siniestro_id)
            .order_by(AccesoEvidenciaDB.id)
        )
        return [
            AccesoEvidencia(
                siniestro_id=fila.siniestro_id,
                evidencia_id=fila.evidencia_id,
                accion=fila.accion,
                actor_id=fila.actor_id,
                rol=fila.rol,
                ip=fila.ip,
                user_agent=fila.user_agent,
                detalle=fila.detalle,
                ocurrido_en=_con_zona(fila.ocurrido_en),
            )
            for fila in self._db.scalars(sentencia).all()
        ]


def _evidencia(registro: EvidenciaSiniestroDB) -> EvidenciaSiniestro:
    return EvidenciaSiniestro(
        evidencia_id=registro.evidencia_id,
        siniestro_id=registro.siniestro_id,
        cliente_id=registro.cliente_id,
        tipo=registro.tipo,
        tipo_contenido=registro.tipo_contenido,
        nombre_archivo=registro.nombre_archivo,
        tamano_bytes=registro.tamano_bytes,
        huella_sha256=registro.huella_sha256,
        capturada_en=_con_zona(registro.capturada_en),
        latitud=registro.latitud,
        longitud=registro.longitud,
        precision_metros=registro.precision_metros,
        subida_por=registro.subida_por,
        subida_en=_con_zona(registro.subida_en),
        clave_almacenamiento=registro.clave_almacenamiento,
    )


def _con_zona(fecha: datetime | None) -> datetime | None:
    """SQLite devuelve las fechas sin zona horaria; se guardan siempre en UTC."""
    if fecha is not None and fecha.tzinfo is None:
        return fecha.replace(tzinfo=UTC)
    return fecha
