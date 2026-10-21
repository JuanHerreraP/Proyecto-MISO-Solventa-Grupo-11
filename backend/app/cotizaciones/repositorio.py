"""Puerto y adaptadores de persistencia para cotizaciones (HU03 / BPM-156)."""

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cotizaciones.dominio.modelos import Cotizacion
from app.cotizaciones.modelos_db import CotizacionDB


class RepositorioCotizaciones(Protocol):
    def guardar(self, cotizacion: Cotizacion) -> None: ...

    def obtener(self, cotizacion_id: str) -> Cotizacion | None: ...

    def listar_por_cliente(self, cliente_id: str) -> list[Cotizacion]: ...


class RepositorioCotizacionesEnMemoria:
    def __init__(self):
        self._por_id: dict[str, Cotizacion] = {}

    def guardar(self, cotizacion: Cotizacion) -> None:
        self._por_id[cotizacion.cotizacion_id] = cotizacion.model_copy(deep=True)

    def obtener(self, cotizacion_id: str) -> Cotizacion | None:
        cotizacion = self._por_id.get(cotizacion_id)
        return cotizacion.model_copy(deep=True) if cotizacion is not None else None

    def listar_por_cliente(self, cliente_id: str) -> list[Cotizacion]:
        cotizaciones = (
            cotizacion
            for cotizacion in self._por_id.values()
            if cotizacion.cliente_id == cliente_id
        )
        return [
            cotizacion.model_copy(deep=True)
            for cotizacion in sorted(
                cotizaciones,
                key=lambda cotizacion: cotizacion.creada_en,
                reverse=True,
            )
        ]


class RepositorioCotizacionesPostgres:
    def __init__(self, db: Session):
        self._db = db

    def guardar(self, cotizacion: Cotizacion) -> None:
        datos = self._a_persistencia(cotizacion)
        persistida = self._db.get(CotizacionDB, cotizacion.cotizacion_id)

        if persistida is None:
            self._db.add(CotizacionDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(persistida, campo, valor)

        self._db.commit()

    def obtener(self, cotizacion_id: str) -> Cotizacion | None:
        return self._a_dominio(self._db.get(CotizacionDB, cotizacion_id))

    def listar_por_cliente(self, cliente_id: str) -> list[Cotizacion]:
        sentencia = (
            select(CotizacionDB)
            .where(CotizacionDB.cliente_id == cliente_id)
            .order_by(CotizacionDB.creada_en.desc())
        )
        return [
            cotizacion
            for registro in self._db.scalars(sentencia).all()
            if (cotizacion := self._a_dominio(registro)) is not None
        ]

    @staticmethod
    def _a_persistencia(cotizacion: Cotizacion) -> dict[str, object]:
        datos = cotizacion.model_dump(mode="json")
        datos.update(
            ramo=cotizacion.ramo.value,
            estado=cotizacion.estado.value,
            prima_total=cotizacion.prima_total,
            creada_en=cotizacion.creada_en,
            vigente_hasta=cotizacion.vigente_hasta,
        )
        return datos

    @staticmethod
    def _a_dominio(persistida: CotizacionDB | None) -> Cotizacion | None:
        if persistida is None:
            return None

        return Cotizacion.model_validate(
            {
                "cotizacion_id": persistida.cotizacion_id,
                "cliente_id": persistida.cliente_id,
                "ramo": persistida.ramo,
                "datos_riesgo": persistida.datos_riesgo,
                "estado": persistida.estado,
                "prima_total": persistida.prima_total,
                "moneda": persistida.moneda,
                "cobertura_principal": persistida.cobertura_principal,
                "perfil_riesgo_id": persistida.perfil_riesgo_id,
                "asesor_id": persistida.asesor_id,
                "socio_id": persistida.socio_id,
                "tenant_id": persistida.tenant_id,
                "creada_en": _con_zona_horaria(persistida.creada_en),
                "vigente_hasta": _con_zona_horaria(persistida.vigente_hasta),
            }
        )


def _con_zona_horaria(fecha: datetime | None) -> datetime | None:
    """Normaliza fechas de SQLite, que puede devolverlas sin zona horaria."""

    if fecha is not None and fecha.tzinfo is None:
        return fecha.replace(tzinfo=UTC)
    return fecha
