"""Casos de uso del cliente sobre sus notificaciones (HU05): bandeja, dispositivos y preferencia.

Todo opera solo sobre lo del cliente que lo pide: una notificación ajena responde como si no
existiera, y un token solo se puede dar de baja por quien lo tiene registrado.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from app.notificaciones.modelos import DispositivoPush, Notificacion, PreferenciaNotificacion
from app.notificaciones.repositorio import (
    RepositorioDispositivos,
    RepositorioNotificaciones,
    RepositorioPreferencias,
)


class NotificacionNoEncontrada(Exception):
    """La notificación no existe o es de otro cliente."""


class ServicioBandeja:
    def __init__(
        self,
        notificaciones: RepositorioNotificaciones,
        dispositivos: RepositorioDispositivos,
        preferencias: RepositorioPreferencias,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        generar_id: Callable[[], str] = lambda: f"DIS-{uuid.uuid4()}",
    ):
        self._notificaciones = notificaciones
        self._dispositivos = dispositivos
        self._preferencias = preferencias
        self._reloj = reloj
        self._generar_id = generar_id

    # --- Bandeja ----------------------------------------------------------------------------

    def listar(
        self, cliente_id: str, limite: int = 50, desplazamiento: int = 0
    ) -> tuple[list[Notificacion], int]:
        """Las notificaciones del cliente, la más reciente primero, y cuántas no ha leído."""
        return (
            self._notificaciones.listar(cliente_id, limite, desplazamiento),
            self._notificaciones.contar_no_leidas(cliente_id),
        )

    def contar_no_leidas(self, cliente_id: str) -> int:
        return self._notificaciones.contar_no_leidas(cliente_id)

    def marcar_leida(self, cliente_id: str, notificacion_id: str) -> int:
        """Marca una notificación como leída (repetirlo no cambia nada) y devuelve las no leídas."""
        if not self._notificaciones.marcar_leida(cliente_id, notificacion_id, self._reloj()):
            raise NotificacionNoEncontrada(notificacion_id)
        return self._notificaciones.contar_no_leidas(cliente_id)

    # --- Dispositivos -----------------------------------------------------------------------

    def registrar_dispositivo(
        self, cliente_id: str, token: str, plataforma: str = "ANDROID"
    ) -> DispositivoPush:
        """Registra el token del teléfono (o lo actualiza). Repetirlo no lo duplica."""
        ahora = self._reloj()
        return self._dispositivos.guardar(
            DispositivoPush(
                dispositivo_id=self._generar_id(),
                cliente_id=cliente_id,
                token=token,
                plataforma=plataforma,
                activo=True,
                registrado_en=ahora,
                actualizado_en=ahora,
            )
        )

    def dar_de_baja_dispositivo(self, cliente_id: str, token: str) -> None:
        """Deja de mandar push a ese teléfono (cierre de sesión). Es tolerante: si el token no
        existe o es de otro cliente, no hace nada y no lo revela."""
        self._dispositivos.desactivar(cliente_id, token, self._reloj())

    # --- Preferencia ------------------------------------------------------------------------

    def push_habilitado(self, cliente_id: str) -> bool:
        preferencia = self._preferencias.obtener(cliente_id)
        return True if preferencia is None else preferencia.push_habilitado

    def cambiar_preferencia(self, cliente_id: str, push_habilitado: bool) -> bool:
        self._preferencias.guardar(
            PreferenciaNotificacion(
                cliente_id=cliente_id,
                push_habilitado=push_habilitado,
                actualizado_en=self._reloj(),
            )
        )
        return push_habilitado
