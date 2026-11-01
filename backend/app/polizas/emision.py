"""Emisión técnica de la póliza y entrega de su documento (HU12).

Flujo: el cliente completa la firma (HU14) -> se emite la póliza -> se compila el PDF y se
guarda una sola vez junto con su huella SHA-256 -> en segundo plano se envían el correo de
bienvenida con el PDF adjunto y la confirmación al cliente.

La emisión es idempotente: el identificador y el número de la póliza se derivan de la
cotización, así que repetirla (reintento de la firma, doble clic, respuesta perdida) devuelve
la misma póliza y el mismo documento.
"""

import calendar
import hashlib
import hmac
import logging
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from app.cotizaciones.repositorio import RepositorioCotizaciones
from app.firmas.modelos import EstadoFirma, ProcesoFirma
from app.firmas.puertos import RepositorioFirmas
from app.polizas.almacenamiento import AlmacenDocumentos, DocumentoInmutable
from app.polizas.comunicaciones import (
    CorreoBienvenida,
    EnviadorCorreo,
    NotificacionEmision,
    Notificador,
)
from app.polizas.dominio.modelos import (
    CoberturaPoliza,
    Poliza,
    RamoPoliza,
    hoy_en_colombia,
)
from app.polizas.pdf import generar_pdf_poliza
from app.polizas.repositorio import RepositorioPolizas
from app.polizas.repositorio_documentos import DocumentoPoliza, RepositorioDocumentos
from app.polizas.servicio import PolizaNoEncontrada

logger = logging.getLogger(__name__)

DIAS_VIGENCIA_POR_DEFECTO = 365


class EmisionNoDisponible(Exception):
    """La cotización no tiene una firma completada, así que aún no se puede emitir."""


class AccesoDenegado(Exception):
    pass


class DocumentoNoDisponible(Exception):
    """La póliza existe pero su documento no está en el almacén."""


class DocumentoAlterado(Exception):
    """El documento guardado no coincide con la huella registrada al emitirlo."""


@dataclass(frozen=True)
class DocumentoDescargable:
    nombre_archivo: str
    contenido: bytes
    huella_sha256: str


def poliza_id_de(cotizacion_id: str) -> str:
    return "POL-" + cotizacion_id.removeprefix("COT-")


def numero_poliza_de(cotizacion_id: str, emitida_en: datetime) -> str:
    sufijo = hashlib.sha256(cotizacion_id.encode()).hexdigest()[:8].upper()
    return f"SOL-{emitida_en.year}-{sufijo}"


def _sumar_meses(inicio: date, meses: int) -> date:
    indice = inicio.year * 12 + (inicio.month - 1) + meses
    anio, mes = divmod(indice, 12)
    dia = min(inicio.day, calendar.monthrange(anio, mes + 1)[1])
    return date(anio, mes + 1, dia)


def _vigencia(ramo: RamoPoliza, datos_riesgo: dict[str, object], firmado_en: datetime):
    """Fechas de cobertura según los datos del riesgo; por defecto un año desde la firma."""

    inicio = hoy_en_colombia(firmado_en)
    if ramo in (RamoPoliza.VIAJE, RamoPoliza.PARAMETRICO):
        try:
            desde = date.fromisoformat(str(datos_riesgo["fecha_inicio"]))
            hasta = date.fromisoformat(str(datos_riesgo["fecha_fin"]))
        except (KeyError, ValueError):
            pass
        else:
            if hasta >= desde:
                return desde, hasta

    for campo in ("meses_cobertura", "plazo_meses"):
        valor = datos_riesgo.get(campo)
        if isinstance(valor, int) and not isinstance(valor, bool) and 0 < valor <= 1200:
            return inicio, _sumar_meses(inicio, valor) - timedelta(days=1)
    return inicio, inicio + timedelta(days=DIAS_VIGENCIA_POR_DEFECTO)


class ServicioEmision:
    def __init__(
        self,
        polizas: RepositorioPolizas,
        documentos: RepositorioDocumentos,
        firmas: RepositorioFirmas,
        cotizaciones: RepositorioCotizaciones,
        almacen: AlmacenDocumentos,
        correo: EnviadorCorreo,
        notificador: Notificador,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        generar_codigo: Callable[[], str] = lambda: secrets.token_hex(8),
    ):
        self._polizas = polizas
        self._documentos = documentos
        self._firmas = firmas
        self._cotizaciones = cotizaciones
        self._almacen = almacen
        self._correo = correo
        self._notificador = notificador
        self._reloj = reloj
        self._generar_codigo = generar_codigo

    # --- Emisión --------------------------------------------------------------------

    def emitir(self, cotizacion_id: str) -> Poliza:
        """Emite la póliza y su documento. Repetirla devuelve lo ya emitido."""

        proceso = self._firmas.obtener_por_cotizacion(cotizacion_id)
        if proceso is None or proceso.estado is not EstadoFirma.FIRMADA:
            raise EmisionNoDisponible(cotizacion_id)

        poliza_id = poliza_id_de(cotizacion_id)
        poliza = self._polizas.obtener(poliza_id)
        if poliza is None:
            poliza = self._construir(proceso, poliza_id)
            try:
                self._polizas.guardar(poliza)
            except Exception:
                # Otra petición emitió al mismo tiempo: se usa la que quedó guardada.
                poliza = self._polizas.obtener(poliza_id)
                if poliza is None:
                    raise
        self._asegurar_documento(poliza, proceso)
        return poliza

    def poliza_emitida(self, cotizacion_id: str) -> str | None:
        poliza_id = poliza_id_de(cotizacion_id)
        return poliza_id if self._documentos.obtener(poliza_id) is not None else None

    def _construir(self, proceso: ProcesoFirma, poliza_id: str) -> Poliza:
        contrato = proceso.contrato
        ahora = self._reloj()
        inicio, fin = _vigencia(
            RamoPoliza(contrato.ramo.value),
            contrato.datos_riesgo,
            proceso.firmado_en or ahora,
        )
        cobertura = contrato.cobertura_principal
        return Poliza(
            poliza_id=poliza_id,
            numero_poliza=numero_poliza_de(proceso.cotizacion_id, ahora),
            cliente_id=proceso.cliente_id,
            cotizacion_id=proceso.cotizacion_id,
            ramo=RamoPoliza(contrato.ramo.value),
            titular_nombre=contrato.titular.nombre_completo,
            titular_tipo_documento=contrato.titular.tipo_documento,
            titular_numero_documento=contrato.titular.numero_documento,
            fecha_inicio=inicio,
            fecha_fin=fin,
            # Lo cobrado, no lo cotizado: el contrato se armó con el monto del pago.
            prima_total=contrato.prima_total,
            moneda=contrato.moneda,
            cobertura_principal=CoberturaPoliza(
                codigo=cobertura.codigo,
                nombre=cobertura.nombre,
                suma_asegurada=cobertura.suma_asegurada,
                descripcion=cobertura.descripcion,
            ),
            codigo_verificacion=self._generar_codigo(),
            emitida_en=ahora,
        )

    def _asegurar_documento(self, poliza: Poliza, proceso: ProcesoFirma) -> DocumentoPoliza:
        existente = self._documentos.obtener(poliza.poliza_id)
        if existente is not None:
            return existente

        clave = f"polizas/{poliza.poliza_id}.pdf"
        contenido = generar_pdf_poliza(poliza, proceso)
        try:
            self._almacen.guardar(clave, contenido)
        except DocumentoInmutable:
            # Quedó un archivo de un intento anterior: es el definitivo, no se reemplaza.
            guardado = self._almacen.leer(clave)
            if guardado is None:
                raise
            contenido = guardado

        documento = DocumentoPoliza(
            poliza_id=poliza.poliza_id,
            clave_almacenamiento=clave,
            huella_sha256=hashlib.sha256(contenido).hexdigest(),
            tamano_bytes=len(contenido),
            creado_en=self._reloj(),
        )
        self._documentos.guardar(documento)
        return documento

    # --- Descarga -------------------------------------------------------------------

    def documento_del_cliente(self, cliente_id: str, poliza_id: str) -> DocumentoDescargable:
        poliza = self._polizas.obtener_del_cliente(poliza_id, cliente_id)
        if poliza is None:
            raise PolizaNoEncontrada(poliza_id)
        return self._descargable(poliza)

    def documento_del_asesor(self, asesor_id: str, poliza_id: str) -> DocumentoDescargable:
        """El asesor solo accede a pólizas de ventas en las que participó."""

        poliza = self._polizas.obtener(poliza_id)
        if poliza is None:
            raise PolizaNoEncontrada(poliza_id)
        cotizacion = (
            self._cotizaciones.obtener(poliza.cotizacion_id) if poliza.cotizacion_id else None
        )
        if cotizacion is None or cotizacion.asesor_id != asesor_id:
            raise AccesoDenegado(poliza_id)
        return self._descargable(poliza)

    def _descargable(self, poliza: Poliza) -> DocumentoDescargable:
        documento = self._documentos.obtener(poliza.poliza_id)
        if documento is None:
            raise DocumentoNoDisponible(poliza.poliza_id)
        contenido = self._leer_verificado(documento)
        return DocumentoDescargable(
            nombre_archivo=f"poliza-{poliza.numero_poliza}.pdf",
            contenido=contenido,
            huella_sha256=documento.huella_sha256,
        )

    def _leer_verificado(self, documento: DocumentoPoliza) -> bytes:
        contenido = self._almacen.leer(documento.clave_almacenamiento)
        if contenido is None:
            raise DocumentoNoDisponible(documento.poliza_id)
        huella = hashlib.sha256(contenido).hexdigest()
        if not hmac.compare_digest(huella, documento.huella_sha256):
            logger.error(
                "El documento de la póliza %s no coincide con su huella", documento.poliza_id
            )
            raise DocumentoAlterado(documento.poliza_id)
        return contenido

    # --- Entrega asíncrona ----------------------------------------------------------

    def notificar(self, poliza_id: str) -> None:
        """Envía el correo de bienvenida y la confirmación, cada uno una sola vez.

        Se ejecuta fuera de la petición. Un fallo se registra y no afecta a la póliza: queda
        pendiente y se reintenta la próxima vez que se llame.
        """

        documento = self._documentos.obtener(poliza_id)
        poliza = self._polizas.obtener(poliza_id)
        if documento is None or poliza is None or poliza.cotizacion_id is None:
            logger.warning("No hay póliza emitida %s para notificar", poliza_id)
            return
        proceso = self._firmas.obtener_por_cotizacion(poliza.cotizacion_id)
        if proceso is None:
            return

        if documento.bienvenida_enviada_en is None:
            try:
                contenido = self._leer_verificado(documento)
                self._correo.enviar_bienvenida(
                    CorreoBienvenida(
                        destinatario=str(proceso.contrato.titular.email),
                        nombre=poliza.titular_nombre,
                        numero_poliza=poliza.numero_poliza,
                        nombre_adjunto=f"poliza-{poliza.numero_poliza}.pdf",
                        adjunto_pdf=contenido,
                    )
                )
                documento = documento.model_copy(update={"bienvenida_enviada_en": self._reloj()})
                self._documentos.guardar(documento)
            except Exception:
                logger.exception("No se pudo enviar el correo de la póliza %s", poliza_id)

        if documento.notificada_en is None:
            try:
                self._notificador.confirmar_emision(
                    NotificacionEmision(
                        cliente_id=poliza.cliente_id,
                        poliza_id=poliza.poliza_id,
                        numero_poliza=poliza.numero_poliza,
                    )
                )
                documento = documento.model_copy(update={"notificada_en": self._reloj()})
                self._documentos.guardar(documento)
            except Exception:
                logger.exception("No se pudo notificar la póliza %s", poliza_id)
