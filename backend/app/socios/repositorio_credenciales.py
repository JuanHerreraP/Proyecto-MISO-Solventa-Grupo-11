"""Puertos y adaptadores para persistir credenciales de socios."""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.socios.dominio.credenciales import CredencialesSocio
from app.socios.modelos_db import CredencialSocioDB


class RepositorioCredencialesSocios(Protocol):
    def guardar(self, credenciales: CredencialesSocio) -> None: ...

    def obtener_por_client_id(self, client_id: str) -> CredencialesSocio | None: ...

    def listar_por_socio(self, socio_id: str) -> list[CredencialesSocio]: ...


class RepositorioCredencialesSociosEnMemoria:
    def __init__(self) -> None:
        self._por_client_id: dict[str, CredencialesSocio] = {}

    def guardar(self, credenciales: CredencialesSocio) -> None:
        self._por_client_id[credenciales.client_id] = credenciales

    def obtener_por_client_id(self, client_id: str) -> CredencialesSocio | None:
        return self._por_client_id.get(client_id)

    def listar_por_socio(self, socio_id: str) -> list[CredencialesSocio]:
        return [
            credenciales
            for credenciales in self._por_client_id.values()
            if credenciales.socio_id == socio_id
        ]


class RepositorioCredencialesSociosPostgres:
    def __init__(self, db: Session) -> None:
        self._db = db

    def guardar(self, credenciales: CredencialesSocio) -> None:
        datos = credenciales.model_dump()
        datos["scopes"] = sorted(scope.value for scope in credenciales.scopes)

        persistida = self._db.get(CredencialSocioDB, credenciales.client_id)
        if persistida is None:
            self._db.add(CredencialSocioDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(persistida, campo, valor)
        self._db.commit()

    def obtener_por_client_id(self, client_id: str) -> CredencialesSocio | None:
        return self._a_dominio(self._db.get(CredencialSocioDB, client_id))

    def listar_por_socio(self, socio_id: str) -> list[CredencialesSocio]:
        sentencia = (
            select(CredencialSocioDB)
            .where(CredencialSocioDB.socio_id == socio_id)
            .order_by(CredencialSocioDB.creado_en)
        )
        return [
            credenciales
            for persistida in self._db.scalars(sentencia).all()
            if (credenciales := self._a_dominio(persistida)) is not None
        ]

    @staticmethod
    def _a_dominio(persistida: CredencialSocioDB | None) -> CredencialesSocio | None:
        if persistida is None:
            return None
        return CredencialesSocio.model_validate(
            {
                "socio_id": persistida.socio_id,
                "tenant_id": persistida.tenant_id,
                "client_id": persistida.client_id,
                "secret_hash": persistida.secret_hash,
                "scopes": persistida.scopes,
                "activo": persistida.activo,
                "creado_en": persistida.creado_en,
            }
        )
