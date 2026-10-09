from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.identidad.modelos_db import UsuarioDB


class RepositorioUsuariosPostgres:
    def __init__(self, db: Session):
        self.db = db

    def buscar_por_email(
        self,
        email: str,
    ) -> UsuarioDB | None:
        sentencia = select(UsuarioDB).where(UsuarioDB.email == email.strip().lower())

        return self.db.scalar(sentencia)

    def guardar(
        self,
        usuario: UsuarioDB,
    ) -> UsuarioDB:
        self.db.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)

        return usuario

    def listar_todos(self) -> list[UsuarioDB]:
        sentencia = select(UsuarioDB).order_by(UsuarioDB.fecha_creacion.desc())

        return list(self.db.scalars(sentencia).all())

    def buscar_por_id(
        self,
        usuario_id: str,
    ):
        return self.db.get(
            UsuarioDB,
            UUID(usuario_id),
        )
