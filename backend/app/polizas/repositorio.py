"""Puertos y adaptadores de persistencia de pólizas y enlaces de certificado (HU07 / BPM-31).

El repositorio nunca devuelve una póliza sin filtrar por titular cuando la consulta viene del
cliente: `obtener_del_cliente` es la única forma de leer una póliza desde la billetera.
"""

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.polizas.dominio.modelos import EnlaceCertificado, Poliza
from app.polizas.modelos_db import EnlaceCertificadoDB, PolizaDB


class RepositorioPolizas(Protocol):
    def guardar(self, poliza: Poliza) -> None: ...

    def listar_por_cliente(self, cliente_id: str) -> list[Poliza]: ...

    def obtener_del_cliente(self, poliza_id: str, cliente_id: str) -> Poliza | None: ...

    def obtener(self, poliza_id: str) -> Poliza | None: ...


class RepositorioEnlaces(Protocol):
    def guardar(self, enlace: EnlaceCertificado) -> None: ...

    def obtener(self, huella_token: str) -> EnlaceCertificado | None: ...


class RepositorioPolizasEnMemoria:
    def __init__(self):
        self._por_id: dict[str, Poliza] = {}

    def guardar(self, poliza: Poliza) -> None:
        self._por_id[poliza.poliza_id] = poliza.model_copy(deep=True)

    def listar_por_cliente(self, cliente_id: str) -> list[Poliza]:
        return [
            poliza.model_copy(deep=True)
            for poliza in self._por_id.values()
            if poliza.cliente_id == cliente_id
        ]

    def obtener_del_cliente(self, poliza_id: str, cliente_id: str) -> Poliza | None:
        poliza = self._por_id.get(poliza_id)
        if poliza is None or poliza.cliente_id != cliente_id:
            return None
        return poliza.model_copy(deep=True)

    def obtener(self, poliza_id: str) -> Poliza | None:
        poliza = self._por_id.get(poliza_id)
        return poliza.model_copy(deep=True) if poliza is not None else None


class RepositorioEnlacesEnMemoria:
    def __init__(self):
        self._por_huella: dict[str, EnlaceCertificado] = {}

    def guardar(self, enlace: EnlaceCertificado) -> None:
        self._por_huella[enlace.huella_token] = enlace.model_copy()

    def obtener(self, huella_token: str) -> EnlaceCertificado | None:
        enlace = self._por_huella.get(huella_token)
        return enlace.model_copy() if enlace is not None else None


class RepositorioPolizasPostgres:
    def __init__(self, db: Session):
        self._db = db

    def guardar(self, poliza: Poliza) -> None:
        datos = _poliza_a_persistencia(poliza)
        persistida = self._db.get(PolizaDB, poliza.poliza_id)
        if persistida is None:
            self._db.add(PolizaDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(persistida, campo, valor)
        self._db.commit()

    def listar_por_cliente(self, cliente_id: str) -> list[Poliza]:
        sentencia = select(PolizaDB).where(PolizaDB.cliente_id == cliente_id)
        return [_poliza_a_dominio(registro) for registro in self._db.scalars(sentencia).all()]

    def obtener_del_cliente(self, poliza_id: str, cliente_id: str) -> Poliza | None:
        sentencia = select(PolizaDB).where(
            PolizaDB.poliza_id == poliza_id,
            PolizaDB.cliente_id == cliente_id,
        )
        registro = self._db.scalars(sentencia).first()
        return _poliza_a_dominio(registro) if registro is not None else None

    def obtener(self, poliza_id: str) -> Poliza | None:
        registro = self._db.get(PolizaDB, poliza_id)
        return _poliza_a_dominio(registro) if registro is not None else None


class RepositorioEnlacesPostgres:
    def __init__(self, db: Session):
        self._db = db

    def guardar(self, enlace: EnlaceCertificado) -> None:
        self._db.add(EnlaceCertificadoDB(**enlace.model_dump()))
        self._db.commit()

    def obtener(self, huella_token: str) -> EnlaceCertificado | None:
        registro = self._db.get(EnlaceCertificadoDB, huella_token)
        if registro is None:
            return None
        return EnlaceCertificado(
            huella_token=registro.huella_token,
            poliza_id=registro.poliza_id,
            cliente_id=registro.cliente_id,
            creado_en=_con_zona_horaria(registro.creado_en),
            expira_en=_con_zona_horaria(registro.expira_en),
        )


def _poliza_a_persistencia(poliza: Poliza) -> dict[str, object]:
    datos = poliza.model_dump()
    datos.update(
        ramo=poliza.ramo.value,
        estado=poliza.estado.value,
        cobertura_principal=poliza.cobertura_principal.model_dump(mode="json"),
    )
    return datos


def _poliza_a_dominio(registro: PolizaDB) -> Poliza:
    return Poliza.model_validate(
        {
            "poliza_id": registro.poliza_id,
            "numero_poliza": registro.numero_poliza,
            "cliente_id": registro.cliente_id,
            "cotizacion_id": registro.cotizacion_id,
            "ramo": registro.ramo,
            "estado": registro.estado,
            "titular_nombre": registro.titular_nombre,
            "titular_tipo_documento": registro.titular_tipo_documento,
            "titular_numero_documento": registro.titular_numero_documento,
            "fecha_inicio": registro.fecha_inicio,
            "fecha_fin": registro.fecha_fin,
            "prima_total": registro.prima_total,
            "moneda": registro.moneda,
            "cobertura_principal": registro.cobertura_principal,
            "codigo_verificacion": registro.codigo_verificacion,
            "emitida_en": _con_zona_horaria(registro.emitida_en),
            "cancelada_en": _con_zona_horaria(registro.cancelada_en),
        }
    )


def _con_zona_horaria(fecha: datetime | None) -> datetime | None:
    """SQLite devuelve las fechas sin zona horaria; se guardan siempre en UTC."""
    if fecha is not None and fecha.tzinfo is None:
        return fecha.replace(tzinfo=UTC)
    return fecha
