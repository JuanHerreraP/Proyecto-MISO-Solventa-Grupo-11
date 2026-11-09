"""Casos de uso de la renovación de la póliza (HU22 / BPM-35).

Flujo: el cliente consulta la propuesta (nueva vigencia, coberturas y prima), la confirma y paga
la cotización de renovación con el recaudo de siempre. Cuando el pago se aprueba, la póliza toma
la nueva vigencia. Si el pago se rechaza, no se completa o la cotización vence, la póliza queda
como estaba y el cliente puede reintentar.

- Consultar calcula la propuesta sin guardar nada. Iniciar crea la cotización de renovación y
  es idempotente: repetirlo devuelve la misma renovación mientras siga vigente.
- Aplicar es idempotente y se dispara desde el pago aprobado (también por la confirmación
  asíncrona de la pasarela). Si falla, la consulta posterior del cliente lo reintenta, así que un
  pago aprobado nunca deja la póliza sin renovar.
- Gestionan la renovación el cliente titular y el asesor de la venta asistida; el pago lo hace el
  cliente.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from app.cotizaciones.dominio.modelos import Cotizacion, EstadoCotizacion, RamoSeguro
from app.cotizaciones.dominio.rating import calcular_prima_y_cobertura
from app.cotizaciones.dominio.validacion import DatosRiesgoInvalidosError
from app.cotizaciones.repositorio import RepositorioCotizaciones
from app.cotizaciones.servicio import VIGENCIA_COTIZACION, generar_cotizacion_id
from app.cotizaciones.servicio_personalizacion import (
    PerfilRiesgoInvalidoError,
    ResultadoPrecioCotizacion,
    RiesgoNoAsegurableError,
    ServicioPersonalizacionCotizacion,
)
from app.identidad.modelos import Rol
from app.pagos.modelos import Pago
from app.pagos.puertos import RepositorioPagos
from app.polizas.acceso import poliza_del_solicitante
from app.polizas.dominio.modelos import EstadoRegistroPoliza, Poliza, hoy_en_colombia
from app.polizas.dominio.renovacion import (
    BloqueoRenovacion,
    CodigoBloqueoRenovacion,
    EstadoRenovacion,
    PropuestaRenovacion,
    Renovacion,
    RenovacionNoEncontrada,
    RenovacionNoPermitida,
    datos_de_renovacion,
    evaluar_bloqueos,
    nueva_vigencia,
    poliza_renovada,
    proponer_renovacion,
    renovacion_id_de,
    sin_precio,
)
from app.polizas.endosos import Solicitante
from app.polizas.repositorio import RepositorioPolizas
from app.polizas.repositorio_renovaciones import RenovacionConcurrente, RepositorioRenovaciones

logger = logging.getLogger(__name__)


def _recortar(valor: str | None, largo: int) -> str | None:
    return valor[:largo] if valor else None


def _bloqueo(codigo: CodigoBloqueoRenovacion, mensaje: str) -> BloqueoRenovacion:
    return BloqueoRenovacion(codigo=codigo, mensaje=mensaje)


@dataclass(frozen=True)
class _Evaluacion:
    """La propuesta y los insumos con los que se calculó, para crear la cotización."""

    propuesta: PropuestaRenovacion
    original: Cotizacion | None = None
    datos_riesgo: dict[str, object] | None = None
    precio: ResultadoPrecioCotizacion | None = None


class ServicioRenovaciones:
    def __init__(
        self,
        polizas: RepositorioPolizas,
        renovaciones: RepositorioRenovaciones,
        cotizaciones: RepositorioCotizaciones,
        personalizador: ServicioPersonalizacionCotizacion,
        pagos: RepositorioPagos,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        generar_id: Callable[[], str] = generar_cotizacion_id,
    ):
        self._polizas = polizas
        self._renovaciones = renovaciones
        self._cotizaciones = cotizaciones
        self._personalizador = personalizador
        self._pagos = pagos
        self._reloj = reloj
        self._generar_id = generar_id

    # --- Propuesta ----------------------------------------------------------------------

    def _evaluar(self, poliza: Poliza, hoy: date) -> _Evaluacion:
        bloqueos = evaluar_bloqueos(poliza, hoy)
        if bloqueos:
            return _Evaluacion(sin_precio(poliza, bloqueos))

        original = (
            self._cotizaciones.obtener(poliza.cotizacion_id) if poliza.cotizacion_id else None
        )
        if original is None:
            return _Evaluacion(
                sin_precio(
                    poliza,
                    [
                        _bloqueo(
                            CodigoBloqueoRenovacion.SIN_DATOS_DE_RIESGO,
                            "No encontramos los datos del riesgo para recalcular la prima.",
                        )
                    ],
                )
            )

        vigencia = nueva_vigencia(poliza, original.datos_riesgo)
        datos = datos_de_renovacion(original.datos_riesgo, vigencia)
        try:
            tarifa = calcular_prima_y_cobertura(RamoSeguro(poliza.ramo.value), datos)
            precio = self._personalizador.personalizar(poliza.cliente_id, tarifa)
        except DatosRiesgoInvalidosError:
            return _Evaluacion(
                sin_precio(
                    poliza,
                    [
                        _bloqueo(
                            CodigoBloqueoRenovacion.SIN_DATOS_DE_RIESGO,
                            "Los datos del riesgo ya no son válidos para cotizar la renovación.",
                        )
                    ],
                )
            )
        except (RiesgoNoAsegurableError, PerfilRiesgoInvalidoError):
            return _Evaluacion(
                sin_precio(
                    poliza,
                    [
                        _bloqueo(
                            CodigoBloqueoRenovacion.RIESGO_NO_ASEGURABLE,
                            "Con tu perfil de riesgo actual no podemos renovar esta póliza.",
                        )
                    ],
                )
            )

        propuesta = proponer_renovacion(poliza, vigencia, precio.prima_total, precio.personalizada)
        return _Evaluacion(propuesta, original, datos, precio)

    def consultar(
        self, solicitante: Solicitante, poliza_id: str
    ) -> tuple[PropuestaRenovacion, Renovacion | None]:
        """La propuesta de renovación y, si hay una en curso esperando el pago, esa renovación."""
        poliza = poliza_del_solicitante(self._polizas, self._cotizaciones, solicitante, poliza_id)
        ahora = self._reloj()
        if self._reconciliar(poliza.poliza_id, ahora):
            poliza = poliza_del_solicitante(
                self._polizas, self._cotizaciones, solicitante, poliza_id
            )
        propuesta = self._evaluar(poliza, hoy_en_colombia(ahora)).propuesta
        pendiente = next(
            (r for r in self._renovaciones.por_poliza(poliza.poliza_id) if r.pendiente_en(ahora)),
            None,
        )
        return propuesta, pendiente

    def obtener(self, solicitante: Solicitante, poliza_id: str, renovacion_id: str) -> Renovacion:
        poliza = poliza_del_solicitante(self._polizas, self._cotizaciones, solicitante, poliza_id)
        self._reconciliar(poliza.poliza_id, self._reloj())
        renovacion = self._renovaciones.obtener(renovacion_id)
        if renovacion is None or renovacion.poliza_id != poliza.poliza_id:
            raise RenovacionNoEncontrada(renovacion_id)
        return renovacion

    def estado_de(self, renovacion: Renovacion) -> EstadoRenovacion:
        """Estado a hoy: una renovación sin pagar cuya cotización venció está vencida."""
        return renovacion.estado_en(self._reloj())

    # --- Inicio -------------------------------------------------------------------------

    def iniciar(
        self,
        solicitante: Solicitante,
        poliza_id: str,
        clave_idempotencia: str | None = None,
    ) -> tuple[Renovacion, bool]:
        """Crea la cotización de renovación. Devuelve la renovación y si se creó ahora."""

        poliza = poliza_del_solicitante(self._polizas, self._cotizaciones, solicitante, poliza_id)
        ahora = self._reloj()

        if clave_idempotencia:
            previa = self._renovaciones.por_clave(poliza.poliza_id, clave_idempotencia)
            if previa is not None and previa.estado_en(ahora) is not EstadoRenovacion.VENCIDA:
                return previa, False

        if self._reconciliar(poliza.poliza_id, ahora):
            poliza = poliza_del_solicitante(
                self._polizas, self._cotizaciones, solicitante, poliza_id
            )
        evaluacion = self._evaluar(poliza, hoy_en_colombia(ahora))
        propuesta = evaluacion.propuesta
        if not propuesta.renovable:
            raise RenovacionNoPermitida(propuesta.bloqueos)

        vigencia = propuesta.nueva_vigencia
        renovacion_id = renovacion_id_de(poliza.poliza_id, vigencia.inicio)
        existente = self._renovaciones.obtener(renovacion_id)
        if existente is not None and existente.pendiente_en(ahora):
            return existente, False

        cotizacion = self._cotizacion_de_renovacion(poliza, evaluacion, solicitante, ahora)
        self._cotizaciones.guardar(cotizacion)
        renovacion = Renovacion(
            renovacion_id=renovacion_id,
            poliza_id=poliza.poliza_id,
            cotizacion_id=cotizacion.cotizacion_id,
            anterior_inicio=poliza.fecha_inicio,
            anterior_fin=poliza.fecha_fin,
            anterior_prima=poliza.prima_total,
            nuevo_inicio=vigencia.inicio,
            nuevo_fin=vigencia.fin,
            prima_principal=propuesta.prima_principal,
            prima_opcionales=propuesta.prima_opcionales,
            prima_total=propuesta.prima_nueva,
            moneda=propuesta.moneda,
            vigente_hasta=cotizacion.vigente_hasta,
            solicitado_por=solicitante.actor_id,
            rol_solicitante=solicitante.rol.value,
            clave_idempotencia=clave_idempotencia or None,
            ip_solicitante=_recortar(solicitante.ip, 64),
            user_agent=_recortar(solicitante.user_agent, 300),
            creado_en=ahora,
        )
        try:
            if existente is None:
                self._renovaciones.crear(renovacion)
            else:
                self._renovaciones.reemplazar_pendiente(renovacion)
        except RenovacionConcurrente:
            # Otra solicitud la creó entre la consulta y el guardado: se devuelve esa.
            actual = self._renovaciones.obtener(renovacion_id)
            if actual is None:
                raise
            return actual, False
        logger.info(
            "Renovación %s de la póliza %s iniciada por %s (%s); prima %s %s",
            renovacion.renovacion_id,
            poliza.poliza_id,
            solicitante.actor_id,
            solicitante.rol.value,
            renovacion.prima_total,
            renovacion.moneda,
        )
        return renovacion, True

    def _cotizacion_de_renovacion(
        self,
        poliza: Poliza,
        evaluacion: _Evaluacion,
        solicitante: Solicitante,
        ahora: datetime,
    ) -> Cotizacion:
        original, precio, propuesta = evaluacion.original, evaluacion.precio, evaluacion.propuesta
        return Cotizacion(
            cotizacion_id=self._generar_id(),
            cliente_id=poliza.cliente_id,
            ramo=RamoSeguro(poliza.ramo.value),
            datos_riesgo=evaluacion.datos_riesgo,
            estado=EstadoCotizacion.VIGENTE,
            prima_total=propuesta.prima_nueva,
            moneda=poliza.moneda,
            cobertura_principal=precio.cobertura_principal,
            perfil_riesgo_id=precio.perfil_riesgo_id,
            asesor_id=solicitante.actor_id if solicitante.rol is Rol.ASESOR_VENTAS else None,
            socio_id=original.socio_id,
            tenant_id=original.tenant_id,
            creada_en=ahora,
            vigente_hasta=ahora + VIGENCIA_COTIZACION,
        )

    # --- Aplicación ---------------------------------------------------------------------

    def aplicar_pago(self, pago: Pago) -> None:
        """Se llama cuando un pago se aprueba. Ignora los pagos que no son de una renovación."""
        renovacion = self._renovaciones.por_cotizacion(pago.cotizacion_id)
        if renovacion is not None:
            self._aplicar(renovacion, pago.pago_id, self._reloj())

    def _reconciliar(self, poliza_id: str, ahora: datetime) -> bool:
        """Aplica las renovaciones con pago aprobado que quedaron sin aplicar."""
        aplicada = False
        for renovacion in self._renovaciones.por_poliza(poliza_id):
            if renovacion.estado is not EstadoRenovacion.PENDIENTE_PAGO:
                continue
            pago = self._pagos.obtener_aprobado_de_cotizacion(renovacion.cotizacion_id)
            if pago is not None:
                resultado = self._aplicar(renovacion, pago.pago_id, ahora)
                aplicada = aplicada or resultado.estado is EstadoRenovacion.APLICADA
        return aplicada

    def _aplicar(self, renovacion: Renovacion, pago_id: str, ahora: datetime) -> Renovacion:
        if renovacion.estado is EstadoRenovacion.APLICADA:
            return renovacion

        poliza = self._polizas.obtener(renovacion.poliza_id)
        motivo = None
        if poliza is None or poliza.estado is EstadoRegistroPoliza.CANCELADA:
            motivo = "La póliza se canceló antes de aplicar la renovación."
        elif poliza.fecha_fin != renovacion.anterior_fin:
            motivo = "La vigencia de la póliza cambió antes de aplicar la renovación."
        if motivo is not None:
            # El cliente ya pagó: queda registrado para gestionar la devolución.
            logger.error("Renovación %s no aplicada: %s", renovacion.renovacion_id, motivo)
            no_aplicada = renovacion.model_copy(
                update={
                    "estado": EstadoRenovacion.NO_APLICADA,
                    "pago_id": pago_id,
                    "motivo_no_aplicada": motivo,
                }
            )
            self._renovaciones.marcar_no_aplicada(no_aplicada)
            return no_aplicada

        aplicada = renovacion.model_copy(
            update={
                "estado": EstadoRenovacion.APLICADA,
                "pago_id": pago_id,
                "aplicada_en": ahora,
            }
        )
        if self._renovaciones.aplicar(aplicada, poliza_renovada(poliza, aplicada)):
            logger.info(
                "Póliza %s renovada hasta %s (pago %s)",
                aplicada.poliza_id,
                aplicada.nuevo_fin,
                pago_id,
            )
        return aplicada
