"""Datos y dobles compartidos por las pruebas de notificaciones."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.notificaciones.modelos import (
    DispositivoPush,
    Notificacion,
    PreferenciaNotificacion,
    TipoNotificacion,
)
from app.notificaciones.repositorio import (
    RepositorioDispositivosEnMemoria,
    RepositorioDispositivosPostgres,
    RepositorioNotificacionesEnMemoria,
    RepositorioNotificacionesPostgres,
    RepositorioPreferenciasEnMemoria,
    RepositorioPreferenciasPostgres,
)
from app.notificaciones.servicio import ServicioNotificaciones

CLIENTE = "CLI-001"
OTRO = "CLI-002"
# 2026-12-10 10:00 en Bogotá (15:00 UTC).
AHORA = datetime(2026, 12, 10, 15, 0, tzinfo=UTC)
HOY = date(2026, 12, 10)


class Reloj:
    def __init__(self, ahora: datetime = AHORA):
        self.ahora = ahora

    def __call__(self) -> datetime:
        return self.ahora

    def avanzar(self, **delta) -> None:
        self.ahora += timedelta(**delta)


def notificacion(
    numero: int = 1,
    cliente_id: str = CLIENTE,
    tipo: TipoNotificacion = TipoNotificacion.ESTADO_SINIESTRO,
    clave: str | None = None,
    dia: date = HOY,
    creada_en: datetime = AHORA,
    **cambios,
) -> Notificacion:
    datos = {
        "notificacion_id": f"NOT-{numero}",
        "cliente_id": cliente_id,
        "tipo": tipo,
        "clave": clave or f"SIN-{numero}:APROBADO",
        "titulo": "Tu siniestro cambió de estado",
        "cuerpo": "Tu siniestro SIN-1 fue aprobado.",
        "datos": {"siniestro_id": f"SIN-{numero}"},
        "dia": dia,
        "creada_en": creada_en,
    }
    datos.update(cambios)
    return Notificacion(**datos)


def dispositivo(
    token: str = "token-aaaa", cliente_id: str = CLIENTE, numero: int = 1, **cambios
) -> DispositivoPush:
    datos = {
        "dispositivo_id": f"DIS-{numero}",
        "cliente_id": cliente_id,
        "token": token,
        "plataforma": "ANDROID",
        "activo": True,
        "registrado_en": AHORA,
        "actualizado_en": AHORA,
    }
    datos.update(cambios)
    return DispositivoPush(**datos)


def preferencia(push_habilitado: bool, cliente_id: str = CLIENTE) -> PreferenciaNotificacion:
    return PreferenciaNotificacion(
        cliente_id=cliente_id, push_habilitado=push_habilitado, actualizado_en=AHORA
    )


class Repositorios:
    """Los tres repositorios del mismo tipo (en memoria o sobre SQLite)."""

    def __init__(self, notificaciones, dispositivos, preferencias):
        self.notificaciones = notificaciones
        self.dispositivos = dispositivos
        self.preferencias = preferencias


def repositorios_en_memoria() -> Repositorios:
    return Repositorios(
        RepositorioNotificacionesEnMemoria(),
        RepositorioDispositivosEnMemoria(),
        RepositorioPreferenciasEnMemoria(),
    )


def repositorios_sqlite():
    """Repositorios sobre una base SQLite en memoria; devuelve (repositorios, cerrar)."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.notificaciones import modelos_db

    for tabla in (
        modelos_db.NotificacionDB,
        modelos_db.DispositivoPushDB,
        modelos_db.PreferenciaNotificacionDB,
    ):
        tabla.__table__.create(engine)
    sesion = sessionmaker(bind=engine)()

    def cerrar() -> None:
        sesion.close()
        engine.dispose()

    return (
        Repositorios(
            RepositorioNotificacionesPostgres(sesion),
            RepositorioDispositivosPostgres(sesion),
            RepositorioPreferenciasPostgres(sesion),
        ),
        cerrar,
    )


def crear_servicio(repos: Repositorios | None = None, reloj: Reloj | None = None):
    repos = repos or repositorios_en_memoria()
    reloj = reloj or Reloj()
    contador = iter(range(1, 10_000))
    servicio = ServicioNotificaciones(
        repos.notificaciones,
        repos.dispositivos,
        repos.preferencias,
        reloj=reloj,
        generar_id=lambda: f"NOT-{next(contador)}",
    )
    return servicio, repos, reloj
