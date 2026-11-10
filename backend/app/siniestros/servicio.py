"""Caso de uso del registro manual de siniestros (HU20, HU04).

Reglas: la póliza debe existir, pertenecer al cliente, estar vigente y cubrir la fecha del
evento, que no puede ser futura. El `cliente_id` sale de la sesión, nunca del cliente.

Con una `Idempotency-Key` (HU04), repetir el mismo registro devuelve el siniestro ya creado:
la app reenvía un borrador después de perder la conexión sin duplicarlo.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from app.polizas.dominio.modelos import EstadoPoliza, hoy_en_colombia
from app.polizas.repositorio import RepositorioPolizas
from app.siniestros.modelos import (
    EstadoSiniestro,
    OrigenSiniestro,
    Siniestro,
    SolicitudSiniestro,
)
from app.siniestros.repositorio import ClaveIdempotenciaDuplicada, RepositorioSiniestros


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


class ClaveIdempotenciaReutilizada(Exception):
    """La misma Idempotency-Key llegó con datos de un siniestro distinto."""


@dataclass(frozen=True)
class RegistroSiniestro:
    """Resultado del registro: `creado` es False cuando se repitió una solicitud ya atendida."""

    siniestro: Siniestro
    creado: bool


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
        return self.registrar(cliente_id, registrado_por, solicitud).siniestro

    def registrar(
        self,
        cliente_id: str,
        registrado_por: str,
        solicitud: SolicitudSiniestro,
        clave_idempotencia: str | None = None,
    ) -> RegistroSiniestro:
        if clave_idempotencia is not None:
            previo = self._siniestros.obtener_por_clave(cliente_id, clave_idempotencia)
            if previo is not None:
                return self._repeticion(previo, solicitud)

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
            tipo_siniestro=solicitud.tipo_siniestro,
            fecha_evento=solicitud.fecha_evento,
            hora_evento=solicitud.hora_evento,
            lugar=solicitud.lugar,
            descripcion=solicitud.descripcion,
            estimacion_danos=solicitud.estimacion_danos,
            moneda="COP",
            registrado_por=registrado_por,
            registrado_en=ahora,
            clave_idempotencia=clave_idempotencia,
        )
        try:
            self._siniestros.guardar(siniestro)
        except ClaveIdempotenciaDuplicada:
            # Dos reintentos simultáneos: gana el primero y el segundo recibe ese siniestro.
            previo = self._siniestros.obtener_por_clave(cliente_id, clave_idempotencia or "")
            if previo is None:
                raise
            return self._repeticion(previo, solicitud)
        return RegistroSiniestro(siniestro=siniestro, creado=True)

    @staticmethod
    def _repeticion(previo: Siniestro, solicitud: SolicitudSiniestro) -> RegistroSiniestro:
        """Devuelve el siniestro ya creado si la solicitud es la misma; si no, es un error."""
        mismos_datos = (
            previo.poliza_id == solicitud.poliza_id
            and previo.fecha_evento == solicitud.fecha_evento
            and previo.hora_evento == solicitud.hora_evento
            and previo.lugar == solicitud.lugar
            and previo.descripcion == solicitud.descripcion
            and previo.estimacion_danos == solicitud.estimacion_danos
            and previo.tipo_siniestro == solicitud.tipo_siniestro
        )
        if not mismos_datos:
            raise ClaveIdempotenciaReutilizada(previo.clave_idempotencia)
        return RegistroSiniestro(siniestro=previo, creado=False)

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
