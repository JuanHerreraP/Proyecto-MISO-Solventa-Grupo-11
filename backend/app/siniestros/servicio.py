"""Caso de uso del registro manual de siniestros (HU20).

Reglas: la póliza debe existir, pertenecer al cliente, estar vigente y cubrir la fecha del
evento, que no puede ser futura. El `cliente_id` sale de la sesión, nunca del cliente.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime

from app.polizas.dominio.modelos import EstadoPoliza, hoy_en_colombia
from app.polizas.repositorio import RepositorioPolizas
from app.siniestros.modelos import (
    EstadoSiniestro,
    OrigenSiniestro,
    Siniestro,
    SolicitudSiniestro,
)
from app.siniestros.repositorio import RepositorioSiniestros


class PolizaNoEncontrada(Exception):
    """La póliza no existe."""


class PolizaAjena(Exception):
    """La póliza no pertenece al cliente autenticado."""


class PolizaNoVigente(Exception):
    """La póliza está vencida o cancelada."""


class FechaEventoInvalida(Exception):
    """El evento cae fuera de la vigencia o es una fecha futura."""

    def __init__(self, codigo: str, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


class ServicioSiniestros:
    def __init__(
        self,
        siniestros: RepositorioSiniestros,
        polizas: RepositorioPolizas,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        generar_id: Callable[[], str] = lambda: f"SIN-{uuid.uuid4()}",
    ):
        self._siniestros = siniestros
        self._polizas = polizas
        self._reloj = reloj
        self._generar_id = generar_id

    def registrar_manual(
        self,
        cliente_id: str,
        registrado_por: str,
        solicitud: SolicitudSiniestro,
    ) -> Siniestro:
        poliza = self._polizas.obtener(solicitud.poliza_id)
        if poliza is None:
            raise PolizaNoEncontrada(solicitud.poliza_id)
        if poliza.cliente_id != cliente_id:
            # Ajena: no se revela si existe para otro titular.
            raise PolizaAjena(solicitud.poliza_id)

        ahora = self._reloj()
        hoy = hoy_en_colombia(ahora)
        if poliza.estado_en(hoy) is not EstadoPoliza.VIGENTE:
            raise PolizaNoVigente(solicitud.poliza_id)

        self._validar_fecha_evento(
            solicitud.fecha_evento, poliza.fecha_inicio, poliza.fecha_fin, hoy
        )

        siniestro = Siniestro(
            siniestro_id=self._generar_id(),
            cliente_id=cliente_id,
            poliza_id=poliza.poliza_id,
            origen=OrigenSiniestro.MANUAL,
            estado=EstadoSiniestro.REGISTRADO,
            fecha_evento=solicitud.fecha_evento,
            hora_evento=solicitud.hora_evento,
            lugar=solicitud.lugar,
            descripcion=solicitud.descripcion,
            estimacion_danos=solicitud.estimacion_danos,
            moneda="COP",
            registrado_por=registrado_por,
            registrado_en=ahora,
        )
        self._siniestros.guardar(siniestro)
        return siniestro

    def listar_de_cliente(self, cliente_id: str) -> list[Siniestro]:
        """Siniestros del cliente, del más reciente al más antiguo."""
        return self._siniestros.listar_por_cliente(cliente_id)

    @staticmethod
    def _validar_fecha_evento(fecha_evento: date, inicio: date, fin: date, hoy: date) -> None:
        if fecha_evento > hoy:
            raise FechaEventoInvalida(
                "FECHA_FUTURA", "La fecha del evento no puede estar en el futuro."
            )
        if fecha_evento < inicio or fecha_evento > fin:
            raise FechaEventoInvalida(
                "FECHA_FUERA_DE_VIGENCIA",
                "La fecha del evento está fuera del periodo cubierto por la póliza.",
            )
