"""Persistencia de desembolsos y cuentas de destino (HU15)."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.desembolsos.modelos import CuentaDesembolso, Desembolso
from app.desembolsos.modelos_db import CuentaDesembolsoDB, DesembolsoDB


class RepositorioDesembolsosEnMemoria:
    def __init__(self):
        self._por_siniestro: dict[str, Desembolso] = {}

    def crear(self, desembolso: Desembolso) -> bool:
        if desembolso.siniestro_id in self._por_siniestro:
            return False
        self._por_siniestro[desembolso.siniestro_id] = desembolso.model_copy()
        return True

    def guardar(self, desembolso: Desembolso) -> None:
        self._por_siniestro[desembolso.siniestro_id] = desembolso.model_copy()

    def obtener_por_siniestro(self, siniestro_id: str) -> Desembolso | None:
        desembolso = self._por_siniestro.get(siniestro_id)
        return desembolso.model_copy() if desembolso is not None else None

    def listar_por_cliente(self, cliente_id: str) -> list[Desembolso]:
        propios = [d for d in self._por_siniestro.values() if d.cliente_id == cliente_id]
        propios.sort(key=lambda d: d.creado_en, reverse=True)
        return [d.model_copy() for d in propios]


class RepositorioCuentasEnMemoria:
    def __init__(self):
        self._por_cliente: dict[str, CuentaDesembolso] = {}

    def guardar(self, cuenta: CuentaDesembolso) -> None:
        self._por_cliente[cuenta.cliente_id] = cuenta.model_copy()

    def obtener(self, cliente_id: str) -> CuentaDesembolso | None:
        cuenta = self._por_cliente.get(cliente_id)
        return cuenta.model_copy() if cuenta is not None else None


class RepositorioDesembolsosPostgres:
    def __init__(self, db: Session):
        self._db = db

    def crear(self, desembolso: Desembolso) -> bool:
        self._db.add(DesembolsoDB(**_a_persistencia(desembolso)))
        try:
            self._db.commit()
        except IntegrityError:
            # Otra aprobación del mismo siniestro llegó primero: ese desembolso es el válido.
            self._db.rollback()
            return False
        return True

    def guardar(self, desembolso: Desembolso) -> None:
        registro = self._db.get(DesembolsoDB, desembolso.desembolso_id)
        datos = _a_persistencia(desembolso)
        if registro is None:
            self._db.add(DesembolsoDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(registro, campo, valor)
        self._db.commit()

    def obtener_por_siniestro(self, siniestro_id: str) -> Desembolso | None:
        sentencia = select(DesembolsoDB).where(DesembolsoDB.siniestro_id == siniestro_id)
        registro = self._db.scalars(sentencia).first()
        return _a_dominio(registro) if registro is not None else None

    def listar_por_cliente(self, cliente_id: str) -> list[Desembolso]:
        sentencia = (
            select(DesembolsoDB)
            .where(DesembolsoDB.cliente_id == cliente_id)
            .order_by(DesembolsoDB.creado_en.desc())
        )
        return [_a_dominio(r) for r in self._db.scalars(sentencia).all()]


class RepositorioCuentasPostgres:
    def __init__(self, db: Session):
        self._db = db

    def guardar(self, cuenta: CuentaDesembolso) -> None:
        datos = cuenta.model_dump()
        datos["tipo_cuenta"] = cuenta.tipo_cuenta.value
        registro = self._db.get(CuentaDesembolsoDB, cuenta.cliente_id)
        if registro is None:
            self._db.add(CuentaDesembolsoDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(registro, campo, valor)
        self._db.commit()

    def obtener(self, cliente_id: str) -> CuentaDesembolso | None:
        registro = self._db.get(CuentaDesembolsoDB, cliente_id)
        if registro is None:
            return None
        return CuentaDesembolso(
            cliente_id=registro.cliente_id,
            codigo_banco=registro.codigo_banco,
            tipo_cuenta=registro.tipo_cuenta,
            ultimos_digitos=registro.ultimos_digitos,
            token_cuenta=registro.token_cuenta,
            registrada_en=_con_zona(registro.registrada_en),
            actualizada_en=_con_zona(registro.actualizada_en),
        )


def _a_persistencia(desembolso: Desembolso) -> dict[str, object]:
    datos = desembolso.model_dump()
    datos.update(medio=desembolso.medio.value, estado=desembolso.estado.value)
    return datos


def _a_dominio(registro: DesembolsoDB) -> Desembolso:
    columnas = {c.name for c in DesembolsoDB.__table__.columns}
    datos = {nombre: getattr(registro, nombre) for nombre in columnas}
    for campo in ("creado_en", "actualizado_en", "completado_en"):
        datos[campo] = _con_zona(datos[campo])
    return Desembolso.model_validate(datos)


def _con_zona(fecha: datetime | None) -> datetime | None:
    """SQLite devuelve las fechas sin zona horaria; se guardan siempre en UTC."""
    if fecha is not None and fecha.tzinfo is None:
        return fecha.replace(tzinfo=UTC)
    return fecha
