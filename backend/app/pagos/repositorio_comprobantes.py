"""Puerto y adaptadores de persistencia de los comprobantes de pago (HU21)."""

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.pagos.modelos import Comprobante
from app.pagos.modelos_db import ComprobanteDB


class RepositorioComprobantes(Protocol):
    def crear(self, comprobante: Comprobante) -> bool:
        """Guarda el comprobante; devuelve False si el pago ya tenía uno."""
        ...

    def por_pago(self, pago_id: str) -> Comprobante | None: ...


class RepositorioComprobantesEnMemoria:
    def __init__(self):
        self._por_pago: dict[str, Comprobante] = {}

    def crear(self, comprobante: Comprobante) -> bool:
        if comprobante.pago_id in self._por_pago:
            return False
        self._por_pago[comprobante.pago_id] = comprobante
        return True

    def por_pago(self, pago_id: str) -> Comprobante | None:
        return self._por_pago.get(pago_id)


class RepositorioComprobantesPostgres:
    def __init__(self, db: Session):
        self._db = db

    def crear(self, comprobante: Comprobante) -> bool:
        self._db.add(ComprobanteDB(**self._a_persistencia(comprobante)))
        try:
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            return False
        return True

    def por_pago(self, pago_id: str) -> Comprobante | None:
        sentencia = select(ComprobanteDB).where(ComprobanteDB.pago_id == pago_id)
        return self._a_dominio(self._db.scalars(sentencia).first())

    @staticmethod
    def _a_persistencia(comprobante: Comprobante) -> dict[str, object]:
        datos = comprobante.model_dump()
        datos.update(concepto=comprobante.concepto.value, metodo=comprobante.metodo.value)
        return datos

    @staticmethod
    def _a_dominio(persistido: ComprobanteDB | None) -> Comprobante | None:
        if persistido is None:
            return None
        datos = {c.name: getattr(persistido, c.name) for c in ComprobanteDB.__table__.columns}
        datos["pagado_en"] = _con_zona(persistido.pagado_en)
        datos["emitido_en"] = _con_zona(persistido.emitido_en)
        return Comprobante.model_validate(datos)


def _con_zona(fecha: datetime) -> datetime:
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=UTC)
