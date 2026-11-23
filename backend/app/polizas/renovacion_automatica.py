"""Casos de uso de la renovación automática de la póliza (HU17 / BPM-69).

Dos entradas:

- El cliente (o el asesor de la venta asistida) consulta y cambia la preferencia: activar o
  desactivar la renovación automática y, solo el cliente, registrar o quitar la tarjeta
  tokenizada con la que se cobra.
- La tarea diaria (`ejecutar`) recorre las pólizas que vencen en los próximos 30 días:
    1. envía una sola vez el preaviso con la prima recalculada (criterio 1);
    2. el día del vencimiento, si la renovación automática sigue activa, crea la renovación de
       HU22 y la cobra con la tarjeta registrada (criterio 2);
    3. con el pago aprobado la póliza toma la nueva vigencia; se emite el documento contractual
       del nuevo periodo y se envía al cliente (criterio 3).
  Además sigue los ciclos abiertos: pagos que la pasarela confirma después, tarjetas que el
  cliente registra tras un rechazo y contratos cuyo envío falló.

Todo es idempotente: cada periodo tiene un único ciclo, el cobro usa una llave derivada de la
cotización y de la tarjeta, y el documento se guarda una sola vez. Ejecutar la tarea dos veces
el mismo día no repite correos ni cobros.
"""

import hashlib
import hmac
import logging
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Protocol

from app.cotizaciones.repositorio import RepositorioCotizaciones
from app.identidad.modelos import Rol
from app.pagos.modelos import EstadoPago, MetodoPago, Pago, SolicitudPago
from app.pagos.puertos import PasarelaNoDisponible, RepositorioPagos
from app.pagos.servicio import CotizacionNoPagable, ServicioPagos
from app.polizas.acceso import poliza_del_solicitante
from app.polizas.almacenamiento import AlmacenDocumentos, DocumentoInmutable
from app.polizas.comunicaciones import (
    CorreoPreavisoRenovacion,
    CorreoRenovacionEmitida,
    CorreoRenovacionNoRealizada,
    EnviadorCorreoRenovacion,
)
from app.polizas.dominio.modelos import Poliza, hoy_en_colombia
from app.polizas.dominio.renovacion import (
    RAMOS_RENOVABLES,
    EstadoRenovacion,
    Renovacion,
    RenovacionNoEncontrada,
    RenovacionNoPermitida,
)
from app.polizas.dominio.renovacion_automatica import (
    DIAS_PREAVISO,
    ESTADOS_FINALES,
    CicloRenovacionAutomatica,
    EstadoCicloRenovacion,
    MedioPagoRegistrado,
    PreferenciaRenovacionAutomatica,
    ResultadoEjecucion,
    candidata,
    ciclo_id_de,
    llave_cobro,
    nuevo_ciclo,
    toca_cobrar,
)
from app.polizas.emision import (
    AccesoDenegado,
    DocumentoAlterado,
    DocumentoDescargable,
    DocumentoNoDisponible,
)
from app.polizas.endosos import Solicitante
from app.polizas.pdf import generar_pdf_renovacion
from app.polizas.renovacion import ServicioRenovaciones
from app.polizas.repositorio import RepositorioPolizas
from app.polizas.repositorio_renovacion_automatica import (
    CicloConcurrente,
    RepositorioCiclos,
    RepositorioPreferencias,
)
from app.polizas.repositorio_renovaciones import RepositorioRenovaciones

logger = logging.getLogger(__name__)


class RenovacionAutomaticaNoDisponible(Exception):
    """El ramo de la póliza no se renueva (se contrata de nuevo cuando se necesita)."""


class DirectorioCorreos(Protocol):
    def correo_de(self, cliente_id: str) -> str | None: ...


class ServicioRenovacionAutomatica:
    def __init__(
        self,
        polizas: RepositorioPolizas,
        cotizaciones: RepositorioCotizaciones,
        preferencias: RepositorioPreferencias,
        ciclos: RepositorioCiclos,
        renovaciones: RepositorioRenovaciones,
        servicio_renovaciones: ServicioRenovaciones,
        pagos: RepositorioPagos,
        servicio_pagos: ServicioPagos,
        almacen: AlmacenDocumentos,
        correo: EnviadorCorreoRenovacion,
        directorio: DirectorioCorreos,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self._polizas = polizas
        self._cotizaciones = cotizaciones
        self._preferencias = preferencias
        self._ciclos = ciclos
        self._renovaciones = renovaciones
        self._servicio_renovaciones = servicio_renovaciones
        self._pagos = pagos
        self._servicio_pagos = servicio_pagos
        self._almacen = almacen
        self._correo = correo
        self._directorio = directorio
        self._reloj = reloj

    # --- Preferencia del cliente ----------------------------------------------------------

    def preferencia_de(self, poliza_id: str) -> PreferenciaRenovacionAutomatica:
        """Sin registro, la renovación automática está activa y sin tarjeta."""
        return self._preferencias.obtener(poliza_id) or PreferenciaRenovacionAutomatica(
            poliza_id=poliza_id
        )

    def consultar(
        self, solicitante: Solicitante, poliza_id: str
    ) -> tuple[Poliza, PreferenciaRenovacionAutomatica, CicloRenovacionAutomatica | None]:
        poliza = poliza_del_solicitante(self._polizas, self._cotizaciones, solicitante, poliza_id)
        ciclos = self._ciclos.por_poliza(poliza.poliza_id)
        return poliza, self.preferencia_de(poliza.poliza_id), (ciclos[0] if ciclos else None)

    def configurar(
        self,
        solicitante: Solicitante,
        poliza_id: str,
        activa: bool,
        medio_pago: MedioPagoRegistrado | None = None,
        quitar_medio_pago: bool = False,
    ) -> PreferenciaRenovacionAutomatica:
        """Activa o desactiva la renovación automática y, si se indica, cambia la tarjeta.

        La tarjeta la registra o la quita solo el cliente titular: el asesor puede ayudarle a
        activar o desactivar la renovación, pero no manejar sus medios de pago.
        """
        poliza = poliza_del_solicitante(self._polizas, self._cotizaciones, solicitante, poliza_id)
        if poliza.ramo not in RAMOS_RENOVABLES:
            raise RenovacionAutomaticaNoDisponible(poliza.poliza_id)
        cambia_medio = medio_pago is not None or quitar_medio_pago
        if cambia_medio and solicitante.rol is not Rol.CLIENTE:
            raise AccesoDenegado(poliza.poliza_id)

        actual = self.preferencia_de(poliza.poliza_id)
        medio = actual.medio_pago
        if quitar_medio_pago:
            medio = None
        if medio_pago is not None:
            medio = medio_pago
        nueva = actual.model_copy(
            update={
                "activa": activa,
                "medio_pago": medio,
                "actualizado_por": solicitante.actor_id,
                "actualizado_en": self._reloj(),
            }
        )
        self._preferencias.guardar(nueva)
        logger.info(
            "Renovación automática de %s %s por %s (%s); tarjeta %s",
            poliza.poliza_id,
            "activada" if activa else "desactivada",
            solicitante.actor_id,
            solicitante.rol.value,
            "registrada" if medio is not None else "sin registrar",
        )
        return nueva

    def documento(
        self, solicitante: Solicitante, poliza_id: str, renovacion_id: str
    ) -> DocumentoDescargable:
        """El documento contractual de un periodo renovado automáticamente."""
        poliza = poliza_del_solicitante(self._polizas, self._cotizaciones, solicitante, poliza_id)
        ciclo = next(
            (
                c
                for c in self._ciclos.por_poliza(poliza.poliza_id)
                if c.renovacion_id == renovacion_id
            ),
            None,
        )
        if ciclo is None:
            raise RenovacionNoEncontrada(renovacion_id)
        if ciclo.clave_documento is None or ciclo.huella_documento is None:
            raise DocumentoNoDisponible(renovacion_id)
        contenido = self._almacen.leer(ciclo.clave_documento)
        if contenido is None:
            raise DocumentoNoDisponible(renovacion_id)
        if not hmac.compare_digest(hashlib.sha256(contenido).hexdigest(), ciclo.huella_documento):
            logger.error(
                "El documento de la renovación %s no coincide con su huella", renovacion_id
            )
            raise DocumentoAlterado(renovacion_id)
        return DocumentoDescargable(
            nombre_archivo=f"renovacion-{poliza.numero_poliza}-{ciclo.vence_el:%Y%m%d}.pdf",
            contenido=contenido,
            huella_sha256=ciclo.huella_documento,
        )

    # --- Tarea diaria ---------------------------------------------------------------------

    def ejecutar(self) -> ResultadoEjecucion:
        """Preavisos, cobros del día y seguimiento de los ciclos abiertos."""
        ahora = self._reloj()
        hoy = hoy_en_colombia(ahora)
        resultado = ResultadoEjecucion(fecha=hoy)
        atendidos: set[str] = set()

        hasta = hoy + timedelta(days=DIAS_PREAVISO)
        for poliza in self._polizas.listar_por_vencer(hoy, hasta):
            if not candidata(poliza, hoy):
                continue
            resultado.revisadas += 1
            # Un ciclo que falla aquí no se reintenta en el seguimiento de esta misma ejecución.
            atendidos.add(ciclo_id_de(poliza.poliza_id, poliza.fecha_fin))
            try:
                self._procesar(poliza, ahora, hoy, resultado)
            except Exception:
                resultado.errores += 1
                logger.exception("Falló la renovación automática de la póliza %s", poliza.poliza_id)

        for ciclo in self._ciclos.abiertos():
            if ciclo.ciclo_id in atendidos:
                continue
            try:
                self._dar_seguimiento(ciclo, ahora, resultado)
            except Exception:
                resultado.errores += 1
                logger.exception("Falló el seguimiento del ciclo %s", ciclo.ciclo_id)

        logger.info("Renovación automática %s: %s", hoy.isoformat(), resultado.model_dump_json())
        return resultado

    def _ciclo_de(self, poliza: Poliza, ahora: datetime) -> CicloRenovacionAutomatica:
        ciclo = nuevo_ciclo(poliza, ahora)
        existente = self._ciclos.obtener(ciclo.ciclo_id)
        if existente is not None:
            return existente
        try:
            self._ciclos.crear(ciclo)
        except CicloConcurrente:
            existente = self._ciclos.obtener(ciclo.ciclo_id)
            if existente is None:
                raise
            return existente
        return ciclo

    def _guardar(
        self, ciclo: CicloRenovacionAutomatica, ahora: datetime, **cambios: object
    ) -> CicloRenovacionAutomatica:
        actualizado = ciclo.model_copy(update={**cambios, "actualizado_en": ahora})
        self._ciclos.guardar(actualizado)
        return actualizado

    def _procesar(
        self, poliza: Poliza, ahora: datetime, hoy: date, resultado: ResultadoEjecucion
    ) -> CicloRenovacionAutomatica:
        ciclo = self._ciclo_de(poliza, ahora)
        if ciclo.estado in ESTADOS_FINALES:
            if ciclo.documento_pendiente:
                ciclo = self._entregar_contrato(ciclo, ahora, resultado)
            return ciclo
        preferencia = self.preferencia_de(poliza.poliza_id)
        if ciclo.preaviso_enviado_en is None:
            ciclo = self._preavisar(poliza, ciclo, preferencia, ahora, resultado)
            if ciclo.estado is EstadoCicloRenovacion.NO_RENOVABLE:
                return ciclo
        if toca_cobrar(poliza, hoy):
            ciclo = self._renovar(poliza, ciclo, preferencia, ahora, resultado)
        return ciclo

    # --- Paso 1: preaviso -----------------------------------------------------------------

    def _preavisar(
        self,
        poliza: Poliza,
        ciclo: CicloRenovacionAutomatica,
        preferencia: PreferenciaRenovacionAutomatica,
        ahora: datetime,
        resultado: ResultadoEjecucion,
    ) -> CicloRenovacionAutomatica:
        propuesta = self._servicio_renovaciones.propuesta_para(poliza, ahora)
        if not propuesta.renovable:
            resultado.no_renovables += 1
            motivo = propuesta.bloqueos[0].mensaje if propuesta.bloqueos else None
            logger.warning("La póliza %s no se puede renovar: %s", poliza.poliza_id, motivo)
            return self._guardar(
                ciclo, ahora, estado=EstadoCicloRenovacion.NO_RENOVABLE, motivo=motivo
            )

        destinatario = self._directorio.correo_de(poliza.cliente_id)
        if destinatario is None:
            # Sin correo no se marca el preaviso: se intenta de nuevo en la próxima ejecución.
            logger.warning("Sin correo para el preaviso de la póliza %s", poliza.poliza_id)
            return ciclo
        medio = preferencia.medio_pago
        self._correo.enviar_preaviso_renovacion(
            CorreoPreavisoRenovacion(
                destinatario=destinatario,
                nombre=poliza.titular_nombre,
                numero_poliza=poliza.numero_poliza,
                nombre_ramo=poliza.nombre_ramo,
                vence_el=poliza.fecha_fin,
                nuevo_inicio=propuesta.nueva_vigencia.inicio,
                nuevo_fin=propuesta.nueva_vigencia.fin,
                prima_actual=propuesta.prima_actual,
                prima_renovacion=propuesta.prima_nueva,
                moneda=propuesta.moneda,
                renovacion_automatica_activa=preferencia.activa,
                tarjeta_ultimos_digitos=medio.ultimos_digitos if medio else None,
            )
        )
        resultado.preavisos += 1
        return self._guardar(
            ciclo,
            ahora,
            preaviso_enviado_en=ahora,
            prima_avisada=propuesta.prima_nueva,
            moneda=propuesta.moneda,
        )

    # --- Paso 2: renovación y cobro -------------------------------------------------------

    def _renovar(
        self,
        poliza: Poliza,
        ciclo: CicloRenovacionAutomatica,
        preferencia: PreferenciaRenovacionAutomatica,
        ahora: datetime,
        resultado: ResultadoEjecucion,
    ) -> CicloRenovacionAutomatica:
        if ciclo.estado is EstadoCicloRenovacion.COBRO_PENDIENTE:
            return self._dar_seguimiento(ciclo, ahora, resultado)
        if not preferencia.activa:
            if ciclo.estado is not EstadoCicloRenovacion.DESACTIVADA:
                resultado.desactivadas += 1
                ciclo = self._guardar(
                    ciclo,
                    ahora,
                    estado=EstadoCicloRenovacion.DESACTIVADA,
                    motivo="El cliente desactivó la renovación automática.",
                )
            return ciclo

        try:
            renovacion, _ = self._servicio_renovaciones.iniciar_automatica(poliza.poliza_id)
        except RenovacionNoPermitida as error:
            resultado.no_renovables += 1
            return self._guardar(
                ciclo,
                ahora,
                estado=EstadoCicloRenovacion.NO_RENOVABLE,
                motivo=error.bloqueos[0].mensaje,
            )
        if renovacion.estado is EstadoRenovacion.APLICADA:
            return self._concluir(ciclo, renovacion, ahora, resultado)
        ciclo = self._guardar(ciclo, ahora, renovacion_id=renovacion.renovacion_id)

        medio = preferencia.medio_pago
        if medio is None:
            return self._sin_medio_de_pago(ciclo, renovacion, ahora, resultado)
        if (
            ciclo.estado is EstadoCicloRenovacion.COBRO_RECHAZADO
            and ciclo.huella_medio_cobrado == medio.huella
        ):
            return ciclo  # Ya se intentó con esta tarjeta; se espera una nueva o el pago manual.
        return self._cobrar(poliza.cliente_id, ciclo, renovacion, medio, ahora, resultado)

    def _sin_medio_de_pago(
        self,
        ciclo: CicloRenovacionAutomatica,
        renovacion: Renovacion,
        ahora: datetime,
        resultado: ResultadoEjecucion,
    ) -> CicloRenovacionAutomatica:
        if ciclo.estado is EstadoCicloRenovacion.SIN_MEDIO_DE_PAGO:
            return ciclo
        resultado.sin_medio_de_pago += 1
        motivo = "No hay una tarjeta registrada para cobrar la renovación."
        ciclo = self._guardar(
            ciclo, ahora, estado=EstadoCicloRenovacion.SIN_MEDIO_DE_PAGO, motivo=motivo
        )
        return self._avisar_no_realizada(ciclo, renovacion, motivo, ahora)

    def _cobrar(
        self,
        cliente_id: str,
        ciclo: CicloRenovacionAutomatica,
        renovacion: Renovacion,
        medio: MedioPagoRegistrado,
        ahora: datetime,
        resultado: ResultadoEjecucion,
    ) -> CicloRenovacionAutomatica:
        llave = llave_cobro(renovacion.cotizacion_id, medio)
        ciclo = self._guardar(
            ciclo,
            ahora,
            huella_medio_cobrado=medio.huella,
            intentos_cobro=ciclo.intentos_cobro + 1,
        )
        solicitud = SolicitudPago(
            cotizacion_id=renovacion.cotizacion_id,
            metodo=MetodoPago.TARJETA,
            token_tarjeta=medio.token_tarjeta,
        )
        try:
            pago, _ = self._servicio_pagos.pagar(cliente_id, llave, solicitud)
        except PasarelaNoDisponible:
            pendiente = self._pagos.obtener_por_llave(cliente_id, llave)
            resultado.pendientes += 1
            return self._guardar(
                ciclo,
                ahora,
                estado=EstadoCicloRenovacion.COBRO_PENDIENTE,
                pago_id=pendiente.pago_id if pendiente else None,
                motivo="La pasarela no respondió; se espera la confirmación del pago.",
            )
        except CotizacionNoPagable as error:
            if error.codigo == "COTIZACION_YA_PAGADA":
                # El cliente la pagó a mano mientras tanto: se sigue como renovación pagada.
                return self._dar_seguimiento(ciclo, ahora, resultado)
            resultado.rechazadas += 1
            return self._rechazo(ciclo, renovacion, f"No se pudo cobrar ({error.codigo}).", ahora)

        ciclo = self._guardar(ciclo, ahora, pago_id=pago.pago_id)
        if pago.estado is EstadoPago.APROBADO:
            actual = self._renovaciones.obtener(renovacion.renovacion_id) or renovacion
            return self._concluir(ciclo, actual, ahora, resultado)
        if pago.estado is EstadoPago.RECHAZADO:
            resultado.rechazadas += 1
            motivo = f"La tarjeta fue rechazada ({pago.motivo_rechazo or 'sin motivo'})."
            return self._rechazo(ciclo, renovacion, motivo, ahora)
        resultado.pendientes += 1
        return self._guardar(ciclo, ahora, estado=EstadoCicloRenovacion.COBRO_PENDIENTE)

    def _rechazo(
        self,
        ciclo: CicloRenovacionAutomatica,
        renovacion: Renovacion,
        motivo: str,
        ahora: datetime,
    ) -> CicloRenovacionAutomatica:
        ciclo = self._guardar(
            ciclo,
            ahora,
            estado=EstadoCicloRenovacion.COBRO_RECHAZADO,
            motivo=motivo[:200],
            aviso_enviado_en=None,
        )
        return self._avisar_no_realizada(ciclo, renovacion, motivo, ahora)

    def _avisar_no_realizada(
        self,
        ciclo: CicloRenovacionAutomatica,
        renovacion: Renovacion,
        motivo: str,
        ahora: datetime,
    ) -> CicloRenovacionAutomatica:
        poliza = self._polizas.obtener(ciclo.poliza_id)
        destinatario = self._directorio.correo_de(poliza.cliente_id) if poliza else None
        if poliza is None or destinatario is None:
            logger.warning("Sin correo para avisar el ciclo %s", ciclo.ciclo_id)
            return ciclo
        try:
            self._correo.enviar_renovacion_no_realizada(
                CorreoRenovacionNoRealizada(
                    destinatario=destinatario,
                    nombre=poliza.titular_nombre,
                    numero_poliza=poliza.numero_poliza,
                    vence_el=ciclo.vence_el,
                    motivo=motivo,
                    pagar_hasta=renovacion.vigente_hasta,
                )
            )
        except Exception:
            logger.exception("No se pudo avisar al cliente del ciclo %s", ciclo.ciclo_id)
            return ciclo
        return self._guardar(ciclo, ahora, aviso_enviado_en=ahora)

    # --- Seguimiento de ciclos abiertos ---------------------------------------------------

    def _dar_seguimiento(
        self, ciclo: CicloRenovacionAutomatica, ahora: datetime, resultado: ResultadoEjecucion
    ) -> CicloRenovacionAutomatica:
        if ciclo.estado is EstadoCicloRenovacion.RENOVADA:
            return self._entregar_contrato(ciclo, ahora, resultado)
        if ciclo.renovacion_id is None:
            return ciclo

        # Aplica los pagos aprobados que hayan quedado sin aplicar (p. ej. por webhook).
        self._servicio_renovaciones.reconciliar(ciclo.poliza_id)
        renovacion = self._renovaciones.obtener(ciclo.renovacion_id)
        if renovacion is None:
            return ciclo
        estado = renovacion.estado_en(ahora)
        if estado in (EstadoRenovacion.APLICADA, EstadoRenovacion.NO_APLICADA):
            return self._concluir(ciclo, renovacion, ahora, resultado)
        if estado is EstadoRenovacion.VENCIDA:
            return self._guardar(
                ciclo,
                ahora,
                estado=EstadoCicloRenovacion.NO_PAGADA,
                motivo="La renovación venció sin un pago aprobado.",
            )

        if ciclo.estado is EstadoCicloRenovacion.COBRO_PENDIENTE:
            pago = self._pagos.obtener(ciclo.pago_id) if ciclo.pago_id else None
            if pago is not None and pago.estado is EstadoPago.RECHAZADO:
                resultado.rechazadas += 1
                motivo = f"La tarjeta fue rechazada ({pago.motivo_rechazo or 'sin motivo'})."
                return self._rechazo(ciclo, renovacion, motivo, ahora)
            return ciclo

        # Sin tarjeta o rechazada: se cobra si el cliente registró una tarjeta nueva.
        preferencia = self.preferencia_de(ciclo.poliza_id)
        medio = preferencia.medio_pago
        if not preferencia.activa:
            return self._guardar(
                ciclo,
                ahora,
                estado=EstadoCicloRenovacion.DESACTIVADA,
                motivo="El cliente desactivó la renovación automática.",
            )
        if medio is None or medio.huella == ciclo.huella_medio_cobrado:
            return ciclo
        poliza = self._polizas.obtener(ciclo.poliza_id)
        if poliza is None:
            return ciclo
        return self._cobrar(poliza.cliente_id, ciclo, renovacion, medio, ahora, resultado)

    # --- Paso 3: documento y envío --------------------------------------------------------

    def _concluir(
        self,
        ciclo: CicloRenovacionAutomatica,
        renovacion: Renovacion,
        ahora: datetime,
        resultado: ResultadoEjecucion,
    ) -> CicloRenovacionAutomatica:
        if renovacion.estado is EstadoRenovacion.PENDIENTE_PAGO:
            # El aviso del pago falló: se aplica ahora.
            self._servicio_renovaciones.reconciliar(ciclo.poliza_id)
            renovacion = self._renovaciones.obtener(renovacion.renovacion_id) or renovacion
        if renovacion.estado is EstadoRenovacion.NO_APLICADA:
            return self._guardar(
                ciclo,
                ahora,
                estado=EstadoCicloRenovacion.NO_APLICADA,
                renovacion_id=renovacion.renovacion_id,
                pago_id=renovacion.pago_id,
                motivo=renovacion.motivo_no_aplicada,
            )
        if renovacion.estado is not EstadoRenovacion.APLICADA:
            return ciclo
        if ciclo.estado is not EstadoCicloRenovacion.RENOVADA:
            resultado.renovadas += 1
            ciclo = self._guardar(
                ciclo,
                ahora,
                estado=EstadoCicloRenovacion.RENOVADA,
                renovacion_id=renovacion.renovacion_id,
                pago_id=renovacion.pago_id,
                motivo=None,
            )
            logger.info(
                "Póliza %s renovada automáticamente hasta %s",
                ciclo.poliza_id,
                renovacion.nuevo_fin.isoformat(),
            )
        return self._entregar_contrato(ciclo, ahora, resultado)

    def _entregar_contrato(
        self, ciclo: CicloRenovacionAutomatica, ahora: datetime, resultado: ResultadoEjecucion
    ) -> CicloRenovacionAutomatica:
        poliza = self._polizas.obtener(ciclo.poliza_id)
        renovacion = (
            self._renovaciones.obtener(ciclo.renovacion_id) if ciclo.renovacion_id else None
        )
        if poliza is None or renovacion is None:
            return ciclo

        contenido: bytes | None = None
        if ciclo.huella_documento is None:
            contenido = self._emitir_documento(poliza, renovacion)
            ciclo = self._guardar(
                ciclo,
                ahora,
                clave_documento=_clave_documento(renovacion),
                huella_documento=hashlib.sha256(contenido).hexdigest(),
                tamano_documento=len(contenido),
            )

        if ciclo.contrato_enviado_en is not None:
            return ciclo
        destinatario = self._directorio.correo_de(poliza.cliente_id)
        if destinatario is None:
            logger.warning("Sin correo para enviar el contrato renovado %s", ciclo.ciclo_id)
            return ciclo
        if contenido is None:
            contenido = self._almacen.leer(ciclo.clave_documento)
            if contenido is None:
                logger.error("No se encontró el documento de la renovación %s", ciclo.ciclo_id)
                return ciclo
        self._correo.enviar_renovacion_emitida(
            CorreoRenovacionEmitida(
                destinatario=destinatario,
                nombre=poliza.titular_nombre,
                numero_poliza=poliza.numero_poliza,
                nuevo_inicio=renovacion.nuevo_inicio,
                nuevo_fin=renovacion.nuevo_fin,
                prima_total=renovacion.prima_total,
                moneda=renovacion.moneda,
                nombre_adjunto=f"renovacion-{poliza.numero_poliza}-{ciclo.vence_el:%Y%m%d}.pdf",
                adjunto_pdf=contenido,
            )
        )
        resultado.contratos_enviados += 1
        return self._guardar(ciclo, ahora, contrato_enviado_en=ahora)

    def _emitir_documento(self, poliza: Poliza, renovacion: Renovacion) -> bytes:
        pago: Pago | None = self._pagos.obtener(renovacion.pago_id) if renovacion.pago_id else None
        clave = _clave_documento(renovacion)
        contenido = generar_pdf_renovacion(poliza, renovacion, pago)
        try:
            self._almacen.guardar(clave, contenido)
        except DocumentoInmutable:
            # Un intento anterior ya dejó el documento: es el definitivo y no se reemplaza.
            guardado = self._almacen.leer(clave)
            if guardado is None:
                raise
            contenido = guardado
        return contenido


def _clave_documento(renovacion: Renovacion) -> str:
    return f"renovaciones/{renovacion.poliza_id}/{renovacion.renovacion_id}.pdf"
