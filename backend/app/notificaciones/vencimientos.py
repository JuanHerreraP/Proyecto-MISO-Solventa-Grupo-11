"""Avisos de vencimiento de pólizas a 15 y 3 días (HU05, criterio 2).

Un proceso externo (EventBridge en AWS) llama una vez al día a `POST
/api/v1/internos/notificaciones/vencimientos`; el backend no tiene tareas programadas propias.
Cada ejecución busca las pólizas que vencen exactamente dentro de 15 y de 3 días y le manda a
su cliente un aviso que, al tocarlo, abre la renovación.

- **Idempotente:** la clave del aviso incluye la póliza, su fecha de fin y el aviso (15 o 3), así
  que ejecutar el job dos veces el mismo día no duplica nada.
- **Solo lo renovable:** las pólizas de los ramos que se pueden renovar y que siguen vigentes.
  Una póliza cancelada o ya vencida no se avisa, y una renovada cambió su fecha de fin y deja de
  coincidir. El seguro de viaje no se renueva, así que no se avisa.
- **Un fallo no frena el lote:** si una póliza no se puede avisar, se cuenta y se sigue.
- **Exacto:** avisa cuando faltan exactamente 15 o 3 días. Si el job no corrió un día, ese aviso
  no se manda solo; se puede ejecutar de nuevo para esa fecha pasando `fecha`.
"""

import logging
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from pydantic import BaseModel

from app.notificaciones.eventos import vencimiento_poliza
from app.notificaciones.servicio import ServicioNotificaciones
from app.polizas.dominio.modelos import EstadoPoliza, hoy_en_colombia
from app.polizas.dominio.renovacion import RAMOS_RENOVABLES
from app.polizas.repositorio import RepositorioPolizas

logger = logging.getLogger(__name__)

# Días antes del vencimiento en que se avisa.
AVISOS_DIAS = (15, 3)


class ResumenAviso(BaseModel):
    dias: int
    # Pólizas que vencían ese día y se podían avisar.
    candidatas: int = 0
    notificadas: int = 0
    # Ya estaban avisadas (el job corrió antes ese día).
    repetidas: int = 0
    errores: int = 0


class ResumenVencimientos(BaseModel):
    fecha: date
    avisos: list[ResumenAviso]


class ServicioVencimientos:
    def __init__(
        self,
        polizas: RepositorioPolizas,
        notificaciones: ServicioNotificaciones,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        avisos_dias: tuple[int, ...] = AVISOS_DIAS,
    ):
        self._polizas = polizas
        self._notificaciones = notificaciones
        self._reloj = reloj
        self._avisos_dias = avisos_dias

    def ejecutar(self, hoy: date | None = None) -> ResumenVencimientos:
        hoy = hoy or hoy_en_colombia(self._reloj())
        return ResumenVencimientos(
            fecha=hoy, avisos=[self._avisar(hoy, dias) for dias in self._avisos_dias]
        )

    def _avisar(self, hoy: date, dias: int) -> ResumenAviso:
        resumen = ResumenAviso(dias=dias)
        for poliza in self._polizas.listar_que_vencen_el(hoy + timedelta(days=dias)):
            if (
                poliza.ramo not in RAMOS_RENOVABLES
                or poliza.estado_en(hoy) is not EstadoPoliza.VIGENTE
            ):
                continue
            resumen.candidatas += 1
            try:
                resultado = self._notificaciones.notificar_evento(
                    poliza.cliente_id, vencimiento_poliza(poliza, dias)
                )
            except Exception:
                logger.exception(
                    "No se pudo avisar el vencimiento de la póliza %s", poliza.poliza_id
                )
                resumen.errores += 1
                continue
            if resultado.nueva:
                resumen.notificadas += 1
            else:
                resumen.repetidas += 1
        return resumen
