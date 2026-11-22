"""Casos de uso de la asistencia en sitio (HU06).

Reglas transversales que el backend valida siempre (el frontend no es autoridad):
  - la póliza existe,
  - la póliza pertenece al cliente autenticado,
  - la póliza está vigente (se reutiliza `Poliza.estado_en`, no se duplica la vigencia),
  - el ramo ofrece ese servicio.

Para consultar prestadores y crear la asistencia se revalida además el prestador (existe, está
activo y ofrece el servicio). No se confía en que el prestador venga de la llamada anterior.

Una asistencia NO requiere un siniestro previo. El `cliente_id` sale de la sesión.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from app.asistencias.modelos import (
    RADIO_KM_MAXIMO,
    RADIO_KM_MINIMO,
    AceptacionAsistencia,
    EstadoAsistencia,
    NuevaAsistencia,
    Prestador,
    SeguimientoAsistencia,
    SolicitudAsistencia,
    TipoServicioAsistencia,
    distancia_km,
    ramo_ofrece_servicio,
)
from app.asistencias.repositorio import RepositorioAsistencias, RepositorioPrestadores
from app.polizas.dominio.modelos import EstadoPoliza, Poliza, hoy_en_colombia
from app.polizas.repositorio import RepositorioPolizas


class PolizaNoEncontrada(Exception):
    """La póliza no existe."""


class PolizaAjena(Exception):
    """La póliza no pertenece al cliente autenticado."""


class PolizaNoVigente(Exception):
    """La póliza está vencida o cancelada."""


class ServicioNoDisponible(Exception):
    """El ramo de la póliza no ofrece el servicio solicitado."""


class PrestadorNoEncontrado(Exception):
    """El prestador no existe."""


class PrestadorNoDisponible(Exception):
    """El prestador está inactivo."""


class ServicioNoOfrecidoPorPrestador(Exception):
    """El prestador no ofrece el servicio seleccionado."""


class RadioInvalido(Exception):
    """El radio de búsqueda está fuera del rango permitido."""


class AsistenciaNoEncontrada(Exception):
    """La asistencia no existe."""


class AsistenciaAjena(Exception):
    """La asistencia pertenece a otro cliente."""


class AsistenciaYaCancelada(Exception):
    """La asistencia ya estaba cancelada."""


class AsistenciaYaAceptada(Exception):
    """La asistencia ya estaba aceptada."""


class AsistenciaCancelada(Exception):
    """La asistencia está cancelada y no admite la operación."""


class TransicionEstadoInvalida(Exception):
    """La operación no es válida para el estado actual de la asistencia."""


class PrestadorConDistancia:
    """Prestador compatible con su distancia a la ubicación del cliente."""

    __slots__ = ("distancia", "prestador", "servicio")

    def __init__(
        self, prestador: Prestador, servicio: TipoServicioAsistencia, distancia: float
    ) -> None:
        self.prestador = prestador
        self.servicio = servicio
        self.distancia = distancia


class ServicioAsistencias:
    def __init__(
        self,
        prestadores: RepositorioPrestadores,
        asistencias: RepositorioAsistencias,
        polizas: RepositorioPolizas,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        generar_id: Callable[[], str] = lambda: f"ASI-{uuid.uuid4()}",
    ) -> None:
        self._prestadores = prestadores
        self._asistencias = asistencias
        self._polizas = polizas
        self._reloj = reloj
        self._generar_id = generar_id

    # -- Consultas -----------------------------------------------------------------------

    def servicios_de_poliza(self, cliente_id: str, poliza_id: str) -> Poliza:
        """Devuelve la póliza validada; la vista deriva los servicios de su ramo."""
        return self._poliza_vigente_del_cliente(cliente_id, poliza_id)

    def prestadores_cercanos(
        self,
        cliente_id: str,
        poliza_id: str,
        servicio: TipoServicioAsistencia,
        latitud: float,
        longitud: float,
        radio_km: float,
    ) -> list[PrestadorConDistancia]:
        if not RADIO_KM_MINIMO <= radio_km <= RADIO_KM_MAXIMO:
            raise RadioInvalido(radio_km)
        poliza = self._poliza_vigente_del_cliente(cliente_id, poliza_id)
        if not ramo_ofrece_servicio(poliza.ramo, servicio):
            raise ServicioNoDisponible(servicio)

        compatibles: list[PrestadorConDistancia] = []
        for prestador in self._prestadores.listar_activos():
            if not prestador.ofrece(servicio):
                continue
            distancia = distancia_km(latitud, longitud, prestador.latitud, prestador.longitud)
            if distancia > radio_km:
                continue
            compatibles.append(PrestadorConDistancia(prestador, servicio, distancia))
        compatibles.sort(key=lambda c: c.distancia)
        return compatibles

    def listar_de_cliente(self, cliente_id: str) -> list[SolicitudAsistencia]:
        return self._asistencias.listar_por_cliente(cliente_id)

    # -- Comandos ------------------------------------------------------------------------

    def crear(
        self, cliente_id: str, solicitud: NuevaAsistencia
    ) -> tuple[SolicitudAsistencia, Prestador]:
        poliza = self._poliza_vigente_del_cliente(cliente_id, solicitud.poliza_id)
        if not ramo_ofrece_servicio(poliza.ramo, solicitud.servicio):
            raise ServicioNoDisponible(solicitud.servicio)

        prestador = self._prestadores.obtener(solicitud.prestador_id)
        if prestador is None:
            raise PrestadorNoEncontrado(solicitud.prestador_id)
        if not prestador.activo:
            raise PrestadorNoDisponible(solicitud.prestador_id)
        if not prestador.ofrece(solicitud.servicio):
            raise ServicioNoOfrecidoPorPrestador(solicitud.prestador_id)

        asistencia = SolicitudAsistencia(
            asistencia_id=self._generar_id(),
            cliente_id=cliente_id,
            poliza_id=poliza.poliza_id,
            prestador_id=prestador.prestador_id,
            servicio=solicitud.servicio,
            latitud=solicitud.latitud,
            longitud=solicitud.longitud,
            observaciones=solicitud.observaciones,
            estado=EstadoAsistencia.SOLICITADA,
            creada_en=self._reloj(),
        )
        self._asistencias.guardar(asistencia)
        return asistencia, prestador

    def cancelar(self, cliente_id: str, asistencia_id: str) -> SolicitudAsistencia:
        asistencia = self._asistencias.obtener(asistencia_id)
        if asistencia is None:
            raise AsistenciaNoEncontrada(asistencia_id)
        if asistencia.cliente_id != cliente_id:
            raise AsistenciaAjena(asistencia_id)
        if asistencia.estado is EstadoAsistencia.CANCELADA:
            raise AsistenciaYaCancelada(asistencia_id)

        cancelada = asistencia.model_copy(
            update={
                "estado": EstadoAsistencia.CANCELADA,
                "cancelada_en": self._reloj(),
            }
        )
        self._asistencias.guardar(cancelada)
        return cancelada

    # -- Operaciones / Siniestros (HU06 ampliación) --------------------------------------

    def listar_para_operaciones(
        self,
        estado: EstadoAsistencia | None = None,
        poliza_id: str | None = None,
        prestador_id: str | None = None,
    ) -> list[SolicitudAsistencia]:
        """Bandeja de seguimiento operativo: todas las asistencias, con filtros opcionales."""
        return self._asistencias.listar(
            estado=estado, poliza_id=poliza_id, prestador_id=prestador_id
        )

    def obtener_para_operaciones(self, asistencia_id: str) -> SolicitudAsistencia:
        asistencia = self._asistencias.obtener(asistencia_id)
        if asistencia is None:
            raise AsistenciaNoEncontrada(asistencia_id)
        return asistencia

    def aceptar(self, asistencia_id: str, solicitud: AceptacionAsistencia) -> SolicitudAsistencia:
        """Operaciones acepta una asistencia SOLICITADA; el ETA es opcional (NULL válido)."""
        asistencia = self._asistencias.obtener(asistencia_id)
        if asistencia is None:
            raise AsistenciaNoEncontrada(asistencia_id)
        if asistencia.estado is EstadoAsistencia.CANCELADA:
            raise AsistenciaCancelada(asistencia_id)
        if asistencia.estado is EstadoAsistencia.ACEPTADA:
            raise AsistenciaYaAceptada(asistencia_id)
        # Solo SOLICITADA -> ACEPTADA.
        aceptada = asistencia.model_copy(
            update={
                "estado": EstadoAsistencia.ACEPTADA,
                "aceptada_en": self._reloj(),
                "tiempo_estimado_llegada_minutos": solicitud.tiempo_estimado_llegada_minutos,
            }
        )
        self._asistencias.guardar(aceptada)
        return aceptada

    def actualizar_seguimiento(
        self, asistencia_id: str, solicitud: SeguimientoAsistencia
    ) -> SolicitudAsistencia:
        """Operaciones actualiza el ETA de una asistencia ya ACEPTADA (puede ponerlo o quitarlo)."""
        asistencia = self._asistencias.obtener(asistencia_id)
        if asistencia is None:
            raise AsistenciaNoEncontrada(asistencia_id)
        if asistencia.estado is not EstadoAsistencia.ACEPTADA:
            # El ETA solo tiene sentido cuando la asistencia está ACEPTADA.
            raise TransicionEstadoInvalida(asistencia_id)
        actualizada = asistencia.model_copy(
            update={"tiempo_estimado_llegada_minutos": solicitud.tiempo_estimado_llegada_minutos}
        )
        self._asistencias.guardar(actualizada)
        return actualizada

    # -- Interno -------------------------------------------------------------------------

    def _poliza_vigente_del_cliente(self, cliente_id: str, poliza_id: str) -> Poliza:
        poliza = self._polizas.obtener(poliza_id)
        if poliza is None:
            raise PolizaNoEncontrada(poliza_id)
        if poliza.cliente_id != cliente_id:
            # Ajena: no se revela si existe para otro titular.
            raise PolizaAjena(poliza_id)
        hoy = hoy_en_colombia(self._reloj())
        if poliza.estado_en(hoy) is not EstadoPoliza.VIGENTE:
            raise PolizaNoVigente(poliza_id)
        return poliza
