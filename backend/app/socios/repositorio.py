"""Puertos y adaptadores de persistencia para socios."""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.socios.dominio.auditoria import AccionAuditoria, RegistroAuditoriaSocio
from app.socios.dominio.modelos import SocioDistribucion
from app.socios.modelos_db import EventoAuditoriaSocioDB, SocioDistribucionDB


class RepositorioSocios(Protocol):
    def guardar(self, socio: SocioDistribucion) -> None: ...

    def obtener(self, socio_id: str) -> SocioDistribucion | None: ...

    def obtener_por_nit(self, nit: str) -> SocioDistribucion | None: ...


class RepositorioSociosEnMemoria:
    def __init__(self):
        self._por_id: dict[str, SocioDistribucion] = {}
        self._id_por_nit: dict[str, str] = {}

    def guardar(self, socio: SocioDistribucion) -> None:
        self._por_id[socio.socio_id] = socio
        self._id_por_nit[socio.nit] = socio.socio_id

    def obtener(self, socio_id: str) -> SocioDistribucion | None:
        return self._por_id.get(socio_id)

    def obtener_por_nit(self, nit: str) -> SocioDistribucion | None:
        socio_id = self._id_por_nit.get(nit)
        return self._por_id.get(socio_id) if socio_id is not None else None


class RepositorioSociosPostgres:
    def __init__(self, db: Session):
        self._db = db

    def guardar(self, socio: SocioDistribucion) -> None:
        datos = socio.model_dump()
        datos["endpoints_autorizados"] = sorted(
            endpoint.value for endpoint in socio.endpoints_autorizados
        )
        datos["tipos_seguros_autorizados"] = [
            tipo.value for tipo in socio.tipos_seguros_autorizados
        ]

        persistido = self._db.get(SocioDistribucionDB, socio.socio_id)
        if persistido is None:
            self._db.add(SocioDistribucionDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(persistido, campo, valor)
        self._db.commit()

    def obtener(self, socio_id: str) -> SocioDistribucion | None:
        return self._a_dominio(self._db.get(SocioDistribucionDB, socio_id))

    def obtener_por_nit(self, nit: str) -> SocioDistribucion | None:
        sentencia = select(SocioDistribucionDB).where(SocioDistribucionDB.nit == nit)
        return self._a_dominio(self._db.scalar(sentencia))

    @staticmethod
    def _a_dominio(persistido: SocioDistribucionDB | None) -> SocioDistribucion | None:
        if persistido is None:
            return None
        return SocioDistribucion.model_validate(
            {
                "socio_id": persistido.socio_id,
                "tenant_id": persistido.tenant_id,
                "nit": persistido.nit,
                "razon_social": persistido.razon_social,
                "contactos_tecnicos": persistido.contactos_tecnicos,
                "pais_operacion": persistido.pais_operacion,
                "tipos_seguros_autorizados": persistido.tipos_seguros_autorizados,
                "endpoints_autorizados": persistido.endpoints_autorizados,
                "estado": persistido.estado,
                "creado_en": persistido.creado_en,
                "actualizado_en": persistido.actualizado_en,
            }
        )


class RepositorioAuditoriaSociosPostgres:
    def __init__(self, db: Session):
        self._db = db

    def registrar(self, registro: RegistroAuditoriaSocio) -> None:
        datos = registro.model_dump()
        datos["accion"] = registro.accion.value
        self._db.add(EventoAuditoriaSocioDB(**datos))
        self._db.commit()

    def listar_por_socio(self, socio_id: str) -> list[RegistroAuditoriaSocio]:
        sentencia = (
            select(EventoAuditoriaSocioDB)
            .where(EventoAuditoriaSocioDB.socio_id == socio_id)
            .order_by(EventoAuditoriaSocioDB.fecha)
        )
        return [
            RegistroAuditoriaSocio(
                auditoria_id=registro.auditoria_id,
                socio_id=registro.socio_id,
                actor_id=registro.actor_id,
                accion=AccionAuditoria(registro.accion),
                campos_modificados=registro.campos_modificados,
                fecha=registro.fecha,
            )
            for registro in self._db.scalars(sentencia).all()
        ]
