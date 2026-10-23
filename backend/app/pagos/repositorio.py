"""Adaptadores de persistencia de pagos (HU13)."""

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.pagos.modelos import EstadoPago, Pago
from app.pagos.modelos_db import PagoDB


class RepositorioPagosEnMemoria:
    def __init__(self):
        self._por_id: dict[str, Pago] = {}

    def crear(self, pago: Pago) -> bool:
        if self.obtener_por_llave(pago.cliente_id, pago.idempotency_key) is not None:
            return False
        self._por_id[pago.pago_id] = pago.model_copy(deep=True)
        return True

    def guardar(self, pago: Pago) -> None:
        self._por_id[pago.pago_id] = pago.model_copy(deep=True)

    def obtener(self, pago_id: str) -> Pago | None:
        pago = self._por_id.get(pago_id)
        return pago.model_copy(deep=True) if pago else None

    def obtener_por_llave(self, cliente_id: str, idempotency_key: str) -> Pago | None:
        return self._buscar(
            lambda p: p.cliente_id == cliente_id and p.idempotency_key == idempotency_key
        )

    def obtener_por_referencia(self, referencia_pasarela: str) -> Pago | None:
        return self._buscar(lambda p: p.referencia_pasarela == referencia_pasarela)

    def obtener_aprobado_de_cotizacion(self, cotizacion_id: str) -> Pago | None:
        return self._buscar(
            lambda p: p.cotizacion_id == cotizacion_id and p.estado is EstadoPago.APROBADO
        )

    def listar_de_cliente(self, cliente_id: str) -> list[Pago]:
        propios = [p for p in self._por_id.values() if p.cliente_id == cliente_id]
        propios.sort(key=lambda p: p.creado_en, reverse=True)
        return [p.model_copy(deep=True) for p in propios]

    def _buscar(self, criterio: Callable[[Pago], bool]) -> Pago | None:
        for pago in self._por_id.values():
            if criterio(pago):
                return pago.model_copy(deep=True)
        return None


class RepositorioPagosPostgres:
    def __init__(self, db: Session):
        self._db = db

    def crear(self, pago: Pago) -> bool:
        self._db.add(PagoDB(**self._a_persistencia(pago)))
        try:
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            return False
        return True

    def guardar(self, pago: Pago) -> None:
        persistido = self._db.get(PagoDB, pago.pago_id)
        datos = self._a_persistencia(pago)
        if persistido is None:
            self._db.add(PagoDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(persistido, campo, valor)
        self._db.commit()

    def obtener(self, pago_id: str) -> Pago | None:
        return self._a_dominio(self._db.get(PagoDB, pago_id))

    def obtener_por_llave(self, cliente_id: str, idempotency_key: str) -> Pago | None:
        sentencia = select(PagoDB).where(
            PagoDB.cliente_id == cliente_id, PagoDB.idempotency_key == idempotency_key
        )
        return self._a_dominio(self._db.scalars(sentencia).first())

    def obtener_por_referencia(self, referencia_pasarela: str) -> Pago | None:
        sentencia = select(PagoDB).where(PagoDB.referencia_pasarela == referencia_pasarela)
        return self._a_dominio(self._db.scalars(sentencia).first())

    def obtener_aprobado_de_cotizacion(self, cotizacion_id: str) -> Pago | None:
        sentencia = select(PagoDB).where(
            PagoDB.cotizacion_id == cotizacion_id, PagoDB.estado == EstadoPago.APROBADO.value
        )
        return self._a_dominio(self._db.scalars(sentencia).first())

    def listar_de_cliente(self, cliente_id: str) -> list[Pago]:
        sentencia = (
            select(PagoDB).where(PagoDB.cliente_id == cliente_id).order_by(PagoDB.creado_en.desc())
        )
        return [self._a_dominio(fila) for fila in self._db.scalars(sentencia)]

    @staticmethod
    def _a_persistencia(pago: Pago) -> dict[str, object]:
        datos = pago.model_dump()
        datos.update(metodo=pago.metodo.value, estado=pago.estado.value)
        return datos

    @staticmethod
    def _a_dominio(persistido: PagoDB | None) -> Pago | None:
        if persistido is None:
            return None
        datos = {c.name: getattr(persistido, c.name) for c in PagoDB.__table__.columns}
        datos["creado_en"] = _con_zona(persistido.creado_en)
        datos["actualizado_en"] = _con_zona(persistido.actualizado_en)
        return Pago.model_validate(datos)


def _con_zona(fecha: datetime) -> datetime:
    return fecha.replace(tzinfo=UTC) if fecha.tzinfo is None else fecha
