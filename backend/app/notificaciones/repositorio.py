"""Puertos y adaptadores de persistencia de las notificaciones, dispositivos y preferencias."""

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.notificaciones.modelos import (
    DispositivoPush,
    Notificacion,
    PreferenciaNotificacion,
    TipoNotificacion,
)
from app.notificaciones.modelos_db import (
    DispositivoPushDB,
    NotificacionDB,
    PreferenciaNotificacionDB,
)


def _con_zona(fecha: datetime | None) -> datetime | None:
    if fecha is None:
        return None
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=UTC)


# --- Notificaciones ------------------------------------------------------------------------


class RepositorioNotificaciones(Protocol):
    def crear(self, notificacion: Notificacion) -> bool:
        """Guarda la notificación; devuelve False si ese evento ya estaba registrado."""
        ...

    def por_clave(self, cliente_id: str, clave: str) -> Notificacion | None: ...

    def contar_del_grupo(self, cliente_id: str, tipo: TipoNotificacion, dia) -> int:
        """Cuántas notificaciones del cliente hay de ese tipo y de ese día."""
        ...

    def listar(
        self, cliente_id: str, limite: int = 50, desplazamiento: int = 0
    ) -> list[Notificacion]:
        """De la más reciente a la más antigua."""
        ...

    def contar_no_leidas(self, cliente_id: str) -> int: ...

    def marcar_leida(self, cliente_id: str, notificacion_id: str, cuando: datetime) -> bool:
        """Marca una notificación del cliente como leída; False si no existe o es de otro."""
        ...


class RepositorioNotificacionesEnMemoria:
    def __init__(self):
        self._por_id: dict[str, Notificacion] = {}

    def crear(self, notificacion: Notificacion) -> bool:
        if self.por_clave(notificacion.cliente_id, notificacion.clave) is not None:
            return False
        self._por_id[notificacion.notificacion_id] = notificacion
        return True

    def por_clave(self, cliente_id: str, clave: str) -> Notificacion | None:
        return next(
            (n for n in self._por_id.values() if n.cliente_id == cliente_id and n.clave == clave),
            None,
        )

    def contar_del_grupo(self, cliente_id: str, tipo: TipoNotificacion, dia) -> int:
        return sum(
            1
            for n in self._por_id.values()
            if n.cliente_id == cliente_id and n.tipo is tipo and n.dia == dia
        )

    def listar(
        self, cliente_id: str, limite: int = 50, desplazamiento: int = 0
    ) -> list[Notificacion]:
        propias = sorted(
            (n for n in self._por_id.values() if n.cliente_id == cliente_id),
            key=lambda n: n.creada_en,
            reverse=True,
        )
        return propias[desplazamiento : desplazamiento + limite]

    def contar_no_leidas(self, cliente_id: str) -> int:
        return sum(1 for n in self._por_id.values() if n.cliente_id == cliente_id and not n.leida)

    def marcar_leida(self, cliente_id: str, notificacion_id: str, cuando: datetime) -> bool:
        actual = self._por_id.get(notificacion_id)
        if actual is None or actual.cliente_id != cliente_id:
            return False
        if actual.leida_en is None:
            self._por_id[notificacion_id] = actual.model_copy(update={"leida_en": cuando})
        return True


class RepositorioNotificacionesPostgres:
    def __init__(self, db: Session):
        self._db = db

    def crear(self, notificacion: Notificacion) -> bool:
        self._db.add(NotificacionDB(**self._a_persistencia(notificacion)))
        try:
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            return False
        return True

    def por_clave(self, cliente_id: str, clave: str) -> Notificacion | None:
        sentencia = select(NotificacionDB).where(
            NotificacionDB.cliente_id == cliente_id, NotificacionDB.clave == clave
        )
        return self._a_dominio(self._db.scalars(sentencia).first())

    def contar_del_grupo(self, cliente_id: str, tipo: TipoNotificacion, dia) -> int:
        sentencia = (
            select(func.count())
            .select_from(NotificacionDB)
            .where(
                NotificacionDB.cliente_id == cliente_id,
                NotificacionDB.tipo == tipo.value,
                NotificacionDB.dia == dia,
            )
        )
        return self._db.scalar(sentencia) or 0

    def listar(
        self, cliente_id: str, limite: int = 50, desplazamiento: int = 0
    ) -> list[Notificacion]:
        sentencia = (
            select(NotificacionDB)
            .where(NotificacionDB.cliente_id == cliente_id)
            .order_by(NotificacionDB.creada_en.desc())
            .limit(limite)
            .offset(desplazamiento)
        )
        return [self._a_dominio(fila) for fila in self._db.scalars(sentencia)]

    def contar_no_leidas(self, cliente_id: str) -> int:
        sentencia = (
            select(func.count())
            .select_from(NotificacionDB)
            .where(NotificacionDB.cliente_id == cliente_id, NotificacionDB.leida_en.is_(None))
        )
        return self._db.scalar(sentencia) or 0

    def marcar_leida(self, cliente_id: str, notificacion_id: str, cuando: datetime) -> bool:
        fila = self._db.get(NotificacionDB, notificacion_id)
        if fila is None or fila.cliente_id != cliente_id:
            return False
        if fila.leida_en is None:
            self._db.execute(
                update(NotificacionDB)
                .where(NotificacionDB.notificacion_id == notificacion_id)
                .values(leida_en=cuando)
            )
            self._db.commit()
        return True

    @staticmethod
    def _a_persistencia(notificacion: Notificacion) -> dict[str, object]:
        datos = notificacion.model_dump()
        datos["tipo"] = notificacion.tipo.value
        return datos

    @staticmethod
    def _a_dominio(fila: NotificacionDB | None) -> Notificacion | None:
        if fila is None:
            return None
        datos = {c.name: getattr(fila, c.name) for c in NotificacionDB.__table__.columns}
        datos["creada_en"] = _con_zona(fila.creada_en)
        datos["leida_en"] = _con_zona(fila.leida_en)
        return Notificacion.model_validate(datos)


# --- Dispositivos push ---------------------------------------------------------------------


class RepositorioDispositivos(Protocol):
    def guardar(self, dispositivo: DispositivoPush) -> DispositivoPush:
        """Registra el token o lo actualiza. Si ya era de otro cliente, pasa al nuevo."""
        ...

    def activos_de(self, cliente_id: str) -> list[DispositivoPush]: ...

    def desactivar(self, cliente_id: str, token: str, cuando: datetime) -> bool:
        """Da de baja el token del cliente (cierre de sesión); False si no era suyo."""
        ...


class RepositorioDispositivosEnMemoria:
    def __init__(self):
        self._por_token: dict[str, DispositivoPush] = {}

    def guardar(self, dispositivo: DispositivoPush) -> DispositivoPush:
        previo = self._por_token.get(dispositivo.token)
        if previo is not None:
            # Se conserva el identificador y la fecha de registro del dispositivo original.
            dispositivo = dispositivo.model_copy(
                update={
                    "dispositivo_id": previo.dispositivo_id,
                    "registrado_en": previo.registrado_en,
                }
            )
        self._por_token[dispositivo.token] = dispositivo
        return dispositivo

    def activos_de(self, cliente_id: str) -> list[DispositivoPush]:
        return [d for d in self._por_token.values() if d.cliente_id == cliente_id and d.activo]

    def desactivar(self, cliente_id: str, token: str, cuando: datetime) -> bool:
        actual = self._por_token.get(token)
        if actual is None or actual.cliente_id != cliente_id:
            return False
        self._por_token[token] = actual.model_copy(
            update={"activo": False, "actualizado_en": cuando}
        )
        return True


class RepositorioDispositivosPostgres:
    def __init__(self, db: Session):
        self._db = db

    def guardar(self, dispositivo: DispositivoPush) -> DispositivoPush:
        sentencia = select(DispositivoPushDB).where(DispositivoPushDB.token == dispositivo.token)
        fila = self._db.scalars(sentencia).first()
        datos = dispositivo.model_dump()
        if fila is None:
            self._db.add(DispositivoPushDB(**datos))
        else:
            datos.pop("dispositivo_id")
            datos.pop("registrado_en")
            for campo, valor in datos.items():
                setattr(fila, campo, valor)
        self._db.commit()
        return self._a_dominio(self._db.scalars(sentencia).first())

    def activos_de(self, cliente_id: str) -> list[DispositivoPush]:
        sentencia = select(DispositivoPushDB).where(
            DispositivoPushDB.cliente_id == cliente_id, DispositivoPushDB.activo.is_(True)
        )
        return [self._a_dominio(fila) for fila in self._db.scalars(sentencia)]

    def desactivar(self, cliente_id: str, token: str, cuando: datetime) -> bool:
        fila = self._db.scalars(
            select(DispositivoPushDB).where(DispositivoPushDB.token == token)
        ).first()
        if fila is None or fila.cliente_id != cliente_id:
            return False
        fila.activo = False
        fila.actualizado_en = cuando
        self._db.commit()
        return True

    @staticmethod
    def _a_dominio(fila: DispositivoPushDB) -> DispositivoPush:
        datos = {c.name: getattr(fila, c.name) for c in DispositivoPushDB.__table__.columns}
        datos["registrado_en"] = _con_zona(fila.registrado_en)
        datos["actualizado_en"] = _con_zona(fila.actualizado_en)
        return DispositivoPush.model_validate(datos)


# --- Preferencias --------------------------------------------------------------------------


class RepositorioPreferencias(Protocol):
    def obtener(self, cliente_id: str) -> PreferenciaNotificacion | None: ...

    def guardar(self, preferencia: PreferenciaNotificacion) -> None: ...


class RepositorioPreferenciasEnMemoria:
    def __init__(self):
        self._por_cliente: dict[str, PreferenciaNotificacion] = {}

    def obtener(self, cliente_id: str) -> PreferenciaNotificacion | None:
        return self._por_cliente.get(cliente_id)

    def guardar(self, preferencia: PreferenciaNotificacion) -> None:
        self._por_cliente[preferencia.cliente_id] = preferencia


class RepositorioPreferenciasPostgres:
    def __init__(self, db: Session):
        self._db = db

    def obtener(self, cliente_id: str) -> PreferenciaNotificacion | None:
        fila = self._db.get(PreferenciaNotificacionDB, cliente_id)
        if fila is None:
            return None
        return PreferenciaNotificacion(
            cliente_id=fila.cliente_id,
            push_habilitado=fila.push_habilitado,
            actualizado_en=_con_zona(fila.actualizado_en),
        )

    def guardar(self, preferencia: PreferenciaNotificacion) -> None:
        fila = self._db.get(PreferenciaNotificacionDB, preferencia.cliente_id)
        datos = preferencia.model_dump()
        if fila is None:
            self._db.add(PreferenciaNotificacionDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(fila, campo, valor)
        self._db.commit()
