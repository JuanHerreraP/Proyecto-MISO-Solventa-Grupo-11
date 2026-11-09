"""Persistencia y vistas de la asociación asesor-cliente (HU20).

El asesor de ventas registra siniestros en nombre de los clientes que atiende. Para eso
primero debe quedar asociado a ellos. Este módulo resuelve dos preguntas:

- ¿Qué clientes atiende un asesor? (`listar_clientes_de_asesor`)
- ¿Está este asesor asociado a este cliente? (`existe_asociacion`)
"""

import uuid
from typing import Protocol

from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.identidad.asociacion_db import AsesorClienteDB
from app.identidad.modelos_db import UsuarioDB


def _normalizar_id(valor: str) -> str:
    """Normaliza un identificador de usuario a la forma canónica del UUID.

    En PostgreSQL el UUID se guarda con guiones, pero SQLite lo almacena sin ellos.
    Para comparar identificadores de distintas tablas de forma portable, se normaliza
    todo a la representación canónica con guiones. Si no es un UUID válido, se deja igual.
    """
    try:
        return str(uuid.UUID(str(valor)))
    except (ValueError, AttributeError, TypeError):
        return str(valor)


class ClienteDeAsesor(BaseModel):
    """Datos mínimos de un cliente que el asesor necesita para elegirlo."""

    cliente_id: str
    nombre: str
    apellido: str
    email: EmailStr


class RepositorioAsesorCliente(Protocol):
    def asociar(self, asesor_id: str, cliente_id: str) -> None: ...

    def existe_asociacion(self, asesor_id: str, cliente_id: str) -> bool: ...

    def listar_clientes_de_asesor(self, asesor_id: str) -> list[ClienteDeAsesor]: ...


class RepositorioAsesorClienteEnMemoria:
    def __init__(self):
        # asesor_id -> {cliente_id: ClienteDeAsesor}
        self._por_asesor: dict[str, dict[str, ClienteDeAsesor]] = {}

    def asociar(
        self,
        asesor_id: str,
        cliente_id: str,
        cliente: ClienteDeAsesor | None = None,
    ) -> None:
        self._por_asesor.setdefault(asesor_id, {})[cliente_id] = cliente or ClienteDeAsesor(
            cliente_id=cliente_id,
            nombre="Cliente",
            apellido=cliente_id,
            email=f"{cliente_id}@example.com",
        )

    def existe_asociacion(self, asesor_id: str, cliente_id: str) -> bool:
        return cliente_id in self._por_asesor.get(asesor_id, {})

    def listar_clientes_de_asesor(self, asesor_id: str) -> list[ClienteDeAsesor]:
        clientes = list(self._por_asesor.get(asesor_id, {}).values())
        clientes.sort(key=lambda c: (c.nombre.lower(), c.apellido.lower()))
        return clientes


class RepositorioAsesorClientePostgres:
    def __init__(self, db: Session):
        self._db = db

    def asociar(self, asesor_id: str, cliente_id: str) -> None:
        # Se guarda el identificador en forma canónica para comparar siempre igual.
        cliente_id = _normalizar_id(cliente_id)
        asesor_id = _normalizar_id(asesor_id)
        if self.existe_asociacion(asesor_id, cliente_id):
            return
        self._db.add(AsesorClienteDB(asesor_id=asesor_id, cliente_id=cliente_id))
        self._db.commit()

    def existe_asociacion(self, asesor_id: str, cliente_id: str) -> bool:
        sentencia = select(AsesorClienteDB.id).where(
            AsesorClienteDB.asesor_id == _normalizar_id(asesor_id),
            AsesorClienteDB.cliente_id == _normalizar_id(cliente_id),
        )
        return self._db.scalars(sentencia).first() is not None

    def listar_clientes_de_asesor(self, asesor_id: str) -> list[ClienteDeAsesor]:
        # Se leen los identificadores asociados y luego se buscan los usuarios por su UUID.
        # No se hace un JOIN con cast de UUID porque su formato en texto difiere entre
        # PostgreSQL (con guiones) y SQLite (sin guiones), lo que rompía la unión.
        sentencia = select(AsesorClienteDB.cliente_id).where(
            AsesorClienteDB.asesor_id == _normalizar_id(asesor_id)
        )
        clientes: list[ClienteDeAsesor] = []
        for cliente_id in self._db.scalars(sentencia).all():
            try:
                usuario = self._db.get(UsuarioDB, uuid.UUID(str(cliente_id)))
            except (ValueError, TypeError):
                usuario = None
            if usuario is not None:
                clientes.append(
                    ClienteDeAsesor(
                        cliente_id=str(usuario.id),
                        nombre=usuario.nombre,
                        apellido=usuario.apellido,
                        email=usuario.email,
                    )
                )
        clientes.sort(key=lambda c: (c.nombre.lower(), c.apellido.lower()))
        return clientes
