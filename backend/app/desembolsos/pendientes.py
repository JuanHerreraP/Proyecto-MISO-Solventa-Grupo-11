"""Pagos paramétricos que quedaron sin ordenar, para que el barrido los vuelva a publicar.

Hay dos casos, y en los dos pasó un tiempo prudente desde la última actividad:

- Un siniestro paramétrico aprobado sin desembolso: la aprobación se guardó, pero el evento no
  llegó a publicarse (SNS no respondió) o se perdió el consumo.
- Un desembolso PENDIENTE: la red de desembolsos no respondió y los reintentos de la cola se
  agotaron.
"""

from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.desembolsos.modelos import EstadoDesembolso
from app.desembolsos.modelos_db import DesembolsoDB
from app.desembolsos.repositorio import RepositorioDesembolsosEnMemoria
from app.siniestros.modelos import EstadoSiniestro, OrigenSiniestro
from app.siniestros.modelos_db import SiniestroDB
from app.siniestros.repositorio import RepositorioSiniestrosEnMemoria


class RepositorioPendientesPago(Protocol):
    def ids_pendientes(self, antes_de: datetime, limite: int) -> list[str]:
        """Identificadores de siniestro con el pago pendiente desde antes de `antes_de`."""
        ...


class RepositorioPendientesPagoEnMemoria:
    def __init__(
        self,
        siniestros: RepositorioSiniestrosEnMemoria,
        desembolsos: RepositorioDesembolsosEnMemoria,
    ):
        self._siniestros = siniestros
        self._desembolsos = desembolsos

    def ids_pendientes(self, antes_de: datetime, limite: int) -> list[str]:
        ids: list[str] = []
        for siniestro in self._siniestros.listar(EstadoSiniestro.APROBADO, limite=10_000):
            if siniestro.origen is not OrigenSiniestro.AUTOMATICO:
                continue
            desembolso = self._desembolsos.obtener_por_siniestro(siniestro.siniestro_id)
            if desembolso is None:
                pendiente = siniestro.evaluado_en is not None and siniestro.evaluado_en < antes_de
            else:
                pendiente = (
                    desembolso.estado is EstadoDesembolso.PENDIENTE
                    and desembolso.actualizado_en < antes_de
                )
            if pendiente:
                ids.append(siniestro.siniestro_id)
        return ids[:limite]


class RepositorioPendientesPagoPostgres:
    def __init__(self, db: Session):
        self._db = db

    def ids_pendientes(self, antes_de: datetime, limite: int) -> list[str]:
        sin_desembolso = (
            select(SiniestroDB.siniestro_id)
            .outerjoin(DesembolsoDB, DesembolsoDB.siniestro_id == SiniestroDB.siniestro_id)
            .where(
                SiniestroDB.estado == EstadoSiniestro.APROBADO.value,
                SiniestroDB.origen == OrigenSiniestro.AUTOMATICO.value,
                SiniestroDB.evaluado_en < antes_de,
                DesembolsoDB.desembolso_id.is_(None),
            )
            .limit(limite)
        )
        ids = list(self._db.scalars(sin_desembolso))
        if len(ids) >= limite:
            return ids

        con_desembolso_pendiente = (
            select(DesembolsoDB.siniestro_id)
            .join(SiniestroDB, SiniestroDB.siniestro_id == DesembolsoDB.siniestro_id)
            .where(
                SiniestroDB.origen == OrigenSiniestro.AUTOMATICO.value,
                DesembolsoDB.estado == EstadoDesembolso.PENDIENTE.value,
                DesembolsoDB.actualizado_en < antes_de,
            )
            .limit(limite - len(ids))
        )
        ids.extend(self._db.scalars(con_desembolso_pendiente))
        return ids
