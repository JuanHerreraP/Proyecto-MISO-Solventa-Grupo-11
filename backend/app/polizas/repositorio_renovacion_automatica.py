"""Persistencia de la renovación automática (HU17 / BPM-69): preferencias y ciclos.

La preferencia guarda el token de la tarjeta, nunca el número. El ciclo se crea una sola vez
por periodo de la póliza (su identificador sale de la póliza y del fin del periodo), así que
dos ejecuciones simultáneas de la tarea no envían dos preavisos ni cobran dos veces.
"""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.polizas.dominio.renovacion_automatica import (
    ESTADOS_CON_SEGUIMIENTO,
    CicloRenovacionAutomatica,
    MedioPagoRegistrado,
    PreferenciaRenovacionAutomatica,
)
from app.polizas.modelos_db import CicloRenovacionAutomaticaDB, PreferenciaRenovacionAutomaticaDB
from app.polizas.repositorio import con_zona_horaria


class CicloConcurrente(Exception):
    """Otra ejecución ya creó el ciclo de ese periodo."""


class RepositorioPreferencias(Protocol):
    def obtener(self, poliza_id: str) -> PreferenciaRenovacionAutomatica | None: ...

    def guardar(self, preferencia: PreferenciaRenovacionAutomatica) -> None: ...


class RepositorioCiclos(Protocol):
    def obtener(self, ciclo_id: str) -> CicloRenovacionAutomatica | None: ...

    def crear(self, ciclo: CicloRenovacionAutomatica) -> None:
        """Lanza `CicloConcurrente` si el ciclo ya existe."""
        ...

    def guardar(self, ciclo: CicloRenovacionAutomatica) -> None: ...

    def por_poliza(self, poliza_id: str) -> list[CicloRenovacionAutomatica]:
        """Ciclos de la póliza, del periodo más reciente al más antiguo."""
        ...

    def abiertos(self) -> list[CicloRenovacionAutomatica]:
        """Ciclos que esperan el pago, una tarjeta nueva o el envío del contrato renovado."""
        ...


class RepositorioPreferenciasEnMemoria:
    def __init__(self):
        self._por_poliza: dict[str, PreferenciaRenovacionAutomatica] = {}

    def obtener(self, poliza_id: str) -> PreferenciaRenovacionAutomatica | None:
        preferencia = self._por_poliza.get(poliza_id)
        return preferencia.model_copy(deep=True) if preferencia is not None else None

    def guardar(self, preferencia: PreferenciaRenovacionAutomatica) -> None:
        self._por_poliza[preferencia.poliza_id] = preferencia.model_copy(deep=True)


class RepositorioCiclosEnMemoria:
    def __init__(self):
        self._por_id: dict[str, CicloRenovacionAutomatica] = {}

    def obtener(self, ciclo_id: str) -> CicloRenovacionAutomatica | None:
        ciclo = self._por_id.get(ciclo_id)
        return ciclo.model_copy(deep=True) if ciclo is not None else None

    def crear(self, ciclo: CicloRenovacionAutomatica) -> None:
        if ciclo.ciclo_id in self._por_id:
            raise CicloConcurrente(ciclo.ciclo_id)
        self._por_id[ciclo.ciclo_id] = ciclo.model_copy(deep=True)

    def guardar(self, ciclo: CicloRenovacionAutomatica) -> None:
        self._por_id[ciclo.ciclo_id] = ciclo.model_copy(deep=True)

    def por_poliza(self, poliza_id: str) -> list[CicloRenovacionAutomatica]:
        ciclos = [
            c.model_copy(deep=True) for c in self._por_id.values() if c.poliza_id == poliza_id
        ]
        return sorted(ciclos, key=lambda c: c.vence_el, reverse=True)

    def abiertos(self) -> list[CicloRenovacionAutomatica]:
        return [c.model_copy(deep=True) for c in self._por_id.values() if c.requiere_seguimiento]


class RepositorioPreferenciasPostgres:
    def __init__(self, db: Session):
        self._db = db

    def obtener(self, poliza_id: str) -> PreferenciaRenovacionAutomatica | None:
        registro = self._db.get(PreferenciaRenovacionAutomaticaDB, poliza_id)
        if registro is None:
            return None
        medio = None
        if registro.token_tarjeta:
            medio = MedioPagoRegistrado(
                token_tarjeta=registro.token_tarjeta, ultimos_digitos=registro.ultimos_digitos
            )
        return PreferenciaRenovacionAutomatica(
            poliza_id=registro.poliza_id,
            activa=registro.activa,
            medio_pago=medio,
            actualizado_por=registro.actualizado_por,
            actualizado_en=con_zona_horaria(registro.actualizado_en),
        )

    def guardar(self, preferencia: PreferenciaRenovacionAutomatica) -> None:
        medio = preferencia.medio_pago
        datos = {
            "poliza_id": preferencia.poliza_id,
            "activa": preferencia.activa,
            "token_tarjeta": medio.token_tarjeta if medio else None,
            "ultimos_digitos": medio.ultimos_digitos if medio else None,
            "actualizado_por": preferencia.actualizado_por,
            "actualizado_en": preferencia.actualizado_en,
        }
        registro = self._db.get(PreferenciaRenovacionAutomaticaDB, preferencia.poliza_id)
        if registro is None:
            self._db.add(PreferenciaRenovacionAutomaticaDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(registro, campo, valor)
        self._db.commit()


class RepositorioCiclosPostgres:
    def __init__(self, db: Session):
        self._db = db

    def obtener(self, ciclo_id: str) -> CicloRenovacionAutomatica | None:
        registro = self._db.get(CicloRenovacionAutomaticaDB, ciclo_id)
        return _a_dominio(registro) if registro is not None else None

    def crear(self, ciclo: CicloRenovacionAutomatica) -> None:
        try:
            self._db.add(CicloRenovacionAutomaticaDB(**_a_persistencia(ciclo)))
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            raise CicloConcurrente(ciclo.ciclo_id) from None

    def guardar(self, ciclo: CicloRenovacionAutomatica) -> None:
        registro = self._db.get(CicloRenovacionAutomaticaDB, ciclo.ciclo_id)
        datos = _a_persistencia(ciclo)
        if registro is None:
            self._db.add(CicloRenovacionAutomaticaDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(registro, campo, valor)
        self._db.commit()

    def por_poliza(self, poliza_id: str) -> list[CicloRenovacionAutomatica]:
        sentencia = (
            select(CicloRenovacionAutomaticaDB)
            .where(CicloRenovacionAutomaticaDB.poliza_id == poliza_id)
            .order_by(CicloRenovacionAutomaticaDB.vence_el.desc())
        )
        return [_a_dominio(r) for r in self._db.scalars(sentencia)]

    def abiertos(self) -> list[CicloRenovacionAutomatica]:
        sentencia = select(CicloRenovacionAutomaticaDB).where(
            CicloRenovacionAutomaticaDB.estado.in_([e.value for e in ESTADOS_CON_SEGUIMIENTO])
        )
        ciclos = [_a_dominio(r) for r in self._db.scalars(sentencia)]
        return [c for c in ciclos if c.requiere_seguimiento]


_FECHAS = (
    "preaviso_enviado_en",
    "contrato_enviado_en",
    "aviso_enviado_en",
    "creado_en",
    "actualizado_en",
)


def _a_persistencia(ciclo: CicloRenovacionAutomatica) -> dict[str, object]:
    datos = ciclo.model_dump()
    datos["estado"] = ciclo.estado.value
    return datos


def _a_dominio(registro: CicloRenovacionAutomaticaDB) -> CicloRenovacionAutomatica:
    columnas = {c.name for c in CicloRenovacionAutomaticaDB.__table__.columns}
    datos = {nombre: getattr(registro, nombre) for nombre in columnas}
    for campo in _FECHAS:
        datos[campo] = con_zona_horaria(datos[campo])
    return CicloRenovacionAutomatica.model_validate(datos)
