from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.identidad.modelos_db import SesionRefreshDB, UsuarioDB


class RepositorioUsuariosPostgres:
    def __init__(self, db: Session):
        self.db = db

    def buscar_por_email(
        self,
        email: str,
    ) -> UsuarioDB | None:
        sentencia = select(UsuarioDB).where(UsuarioDB.email == email.strip().lower())

        return self.db.scalar(sentencia)

    def buscar_por_documento(
        self,
        tipo_documento: str,
        numero_documento: str,
    ) -> UsuarioDB | None:
        sentencia = select(UsuarioDB).where(
            UsuarioDB.tipo_documento == tipo_documento.strip().upper(),
            UsuarioDB.numero_documento == numero_documento.strip().upper(),
        )
        return self.db.scalar(sentencia)

    def guardar(
        self,
        usuario: UsuarioDB,
    ) -> UsuarioDB:
        self.db.add(usuario)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise
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


class RepositorioSesionesPostgres:
    """Persistencia de los refresh tokens emitidos (tabla `sesiones_refresh`)."""

    def __init__(self, db: Session):
        self.db = db

    def guardar(self, sesion: SesionRefreshDB) -> SesionRefreshDB:
        self.db.add(sesion)
        self.db.commit()
        return sesion

    def buscar(self, jti: str) -> SesionRefreshDB | None:
        return self.db.get(SesionRefreshDB, jti)

    def revocar(
        self,
        jti: str,
        motivo: str,
        reemplazada_por: str | None = None,
    ) -> None:
        sesion = self.buscar(jti)
        if sesion is None or sesion.revocada:
            return

        sesion.revocada = True
        sesion.fecha_revocacion = datetime.now(timezone.utc)
        sesion.motivo_revocacion = motivo
        sesion.reemplazada_por = reemplazada_por
        self.db.commit()

    def revocar_todas_de_usuario(self, usuario_id: str, motivo: str) -> int:
        sentencia = (
            update(SesionRefreshDB)
            .where(
                SesionRefreshDB.usuario_id == UUID(str(usuario_id)),
                SesionRefreshDB.revocada.is_(False),
            )
            .values(
                revocada=True,
                fecha_revocacion=datetime.now(timezone.utc),
                motivo_revocacion=motivo,
            )
        )
        resultado = self.db.execute(sentencia)
        self.db.commit()
        return resultado.rowcount or 0
