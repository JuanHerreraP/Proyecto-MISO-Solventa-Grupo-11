"""Caso de uso: registrar un evento como notificación del cliente y decidir su push.

- **Siempre se registra** en la bandeja del cliente, tenga o no el push habilitado.
- **Es idempotente** por `clave`: el mismo evento registrado dos veces no duplica la
  notificación ni el push.
- **Agrupa** los eventos del mismo tipo del mismo día (hora de Bogotá): el primero del día genera
  un push normal y los siguientes un resumen con la misma `etiqueta`, que en el teléfono
  reemplaza al anterior en vez de apilar avisos repetitivos.

El servicio solo **decide** qué push corresponde (`PushPendiente`); enviarlo es trabajo del canal
de envío, que se conecta aparte.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from app.notificaciones.modelos import (
    MotivoSinPush,
    Notificacion,
    PushPendiente,
    TipoNotificacion,
    grupo_de,
    resumen_de,
)
from app.notificaciones.repositorio import (
    RepositorioDispositivos,
    RepositorioNotificaciones,
    RepositorioPreferencias,
)
from app.polizas.dominio.modelos import hoy_en_colombia


@dataclass(frozen=True)
class ResultadoRegistro:
    notificacion: Notificacion
    # False si el evento ya estaba registrado: no se vuelve a notificar.
    nueva: bool
    push: PushPendiente | None = None
    motivo_sin_push: MotivoSinPush | None = None


class ServicioNotificaciones:
    def __init__(
        self,
        notificaciones: RepositorioNotificaciones,
        dispositivos: RepositorioDispositivos,
        preferencias: RepositorioPreferencias,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        generar_id: Callable[[], str] = lambda: f"NOT-{uuid.uuid4()}",
    ):
        self._notificaciones = notificaciones
        self._dispositivos = dispositivos
        self._preferencias = preferencias
        self._reloj = reloj
        self._generar_id = generar_id

    def registrar(
        self,
        cliente_id: str,
        tipo: TipoNotificacion,
        clave: str,
        titulo: str,
        cuerpo: str,
        datos: dict[str, str] | None = None,
    ) -> ResultadoRegistro:
        existente = self._notificaciones.por_clave(cliente_id, clave)
        if existente is not None:
            return ResultadoRegistro(existente, nueva=False)

        ahora = self._reloj()
        notificacion = Notificacion(
            notificacion_id=self._generar_id(),
            cliente_id=cliente_id,
            tipo=tipo,
            clave=clave,
            titulo=titulo,
            cuerpo=cuerpo,
            datos=datos or {},
            dia=hoy_en_colombia(ahora),
            creada_en=ahora,
        )
        if not self._notificaciones.crear(notificacion):
            # Otra solicitud registró el mismo evento entre la consulta y la inserción.
            return ResultadoRegistro(self._notificaciones.por_clave(cliente_id, clave), nueva=False)

        total = self._notificaciones.contar_del_grupo(cliente_id, tipo, notificacion.dia)
        push, motivo = self._decidir_push(notificacion, total)
        return ResultadoRegistro(notificacion, nueva=True, push=push, motivo_sin_push=motivo)

    def _decidir_push(
        self, notificacion: Notificacion, total: int
    ) -> tuple[PushPendiente | None, MotivoSinPush | None]:
        preferencia = self._preferencias.obtener(notificacion.cliente_id)
        if preferencia is not None and not preferencia.push_habilitado:
            return None, MotivoSinPush.PUSH_DESHABILITADO

        tokens = tuple(d.token for d in self._dispositivos.activos_de(notificacion.cliente_id))
        if not tokens:
            return None, MotivoSinPush.SIN_DISPOSITIVOS

        datos = {"tipo": notificacion.tipo.value, "notificacion_id": notificacion.notificacion_id}
        if total == 1:
            titulo, cuerpo = notificacion.titulo, notificacion.cuerpo
            datos.update(notificacion.datos)
        else:
            # Varios en el día: un resumen que reemplaza al push anterior del grupo. Sin destino
            # propio: el cliente ve todos en su bandeja.
            titulo, cuerpo = resumen_de(notificacion.tipo, total)
        return (
            PushPendiente(
                cliente_id=notificacion.cliente_id,
                tokens=tokens,
                titulo=titulo,
                cuerpo=cuerpo,
                datos=datos,
                etiqueta=grupo_de(notificacion.tipo, notificacion.dia),
                total_del_grupo=total,
            ),
            None,
        )
