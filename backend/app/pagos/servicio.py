"""Caso de uso del recaudo inicial: cobro idempotente y confirmación (HU13)."""

import hashlib
import hmac
import logging
import os
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from app.cotizaciones.dominio.modelos import EstadoCotizacion
from app.cotizaciones.repositorio import RepositorioCotizaciones
from app.pagos.modelos import EstadoPago, MetodoPago, Pago, SolicitudPago
from app.pagos.puertos import (
    PasarelaNoDisponible,
    PasarelaPagos,
    RepositorioPagos,
    ResultadoCobro,
    SolicitudCobro,
)

logger = logging.getLogger(__name__)


class CotizacionNoPagable(Exception):
    """La cotización no existe, no es del cliente, venció o ya fue pagada."""

    def __init__(self, codigo: str):
        super().__init__(codigo)
        self.codigo = codigo


class LlaveIdempotenciaReutilizada(Exception):
    """La misma Idempotency-Key llegó con un cuerpo distinto."""


class PagoNoEncontrado(Exception):
    pass


class FirmaInvalida(Exception):
    pass


def secreto_webhook() -> bytes:
    secreto = os.getenv("PAGOS_WEBHOOK_SECRET")
    if not secreto:
        raise RuntimeError("PAGOS_WEBHOOK_SECRET no está configurado.")
    return secreto.encode()


def firmar(cuerpo: bytes, secreto: bytes) -> str:
    return hmac.new(secreto, cuerpo, hashlib.sha256).hexdigest()


def huella_de(solicitud: SolicitudPago) -> str:
    canonico = solicitud.model_dump_json(exclude_none=True)
    return hashlib.sha256(canonico.encode()).hexdigest()


class ServicioPagos:
    def __init__(
        self,
        pagos: RepositorioPagos,
        cotizaciones: RepositorioCotizaciones,
        pasarela: PasarelaPagos,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        generar_id: Callable[[], str] = lambda: f"PAG-{uuid.uuid4()}",
    ):
        self._pagos = pagos
        self._cotizaciones = cotizaciones
        self._pasarela = pasarela
        self._reloj = reloj
        self._generar_id = generar_id

    def pagar(
        self, cliente_id: str, idempotency_key: str, solicitud: SolicitudPago
    ) -> tuple[Pago, bool]:
        """Procesa el recaudo. Devuelve (pago, repetido): `repetido` si fue un reintento."""

        huella = huella_de(solicitud)
        previo = self._pagos.obtener_por_llave(cliente_id, idempotency_key)
        if previo is not None:
            return self._reproducir(previo, huella), True

        cotizacion = self._cotizaciones.obtener(solicitud.cotizacion_id)
        if cotizacion is None or cotizacion.cliente_id != cliente_id:
            raise CotizacionNoPagable("COTIZACION_NO_ENCONTRADA")
        ahora = self._reloj()
        if self._pagos.obtener_aprobado_de_cotizacion(cotizacion.cotizacion_id) is not None:
            raise CotizacionNoPagable("COTIZACION_YA_PAGADA")
        if cotizacion.estado_en(ahora) is not EstadoCotizacion.VIGENTE:
            raise CotizacionNoPagable("COTIZACION_NO_VIGENTE")
        self._validar_medio(solicitud)

        # El monto sale de la cotización, nunca del cliente.
        pago = Pago(
            pago_id=self._generar_id(),
            cotizacion_id=cotizacion.cotizacion_id,
            cliente_id=cliente_id,
            idempotency_key=idempotency_key,
            huella_solicitud=huella,
            metodo=solicitud.metodo,
            monto=cotizacion.prima_total,
            moneda=cotizacion.moneda,
            creado_en=ahora,
            actualizado_en=ahora,
        )
        # Se persiste antes de llamar a la pasarela: un reintento concurrente o posterior
        # encuentra el intento y no cobra dos veces.
        if not self._pagos.crear(pago):
            previo = self._pagos.obtener_por_llave(cliente_id, idempotency_key)
            return self._reproducir(previo, huella), True

        try:
            resultado = self._pasarela.cobrar(
                SolicitudCobro(
                    referencia_interna=pago.pago_id,
                    monto=pago.monto,
                    moneda=pago.moneda,
                    metodo=solicitud.metodo,
                    token_tarjeta=solicitud.token_tarjeta,
                    codigo_banco=solicitud.codigo_banco,
                    url_retorno=solicitud.url_retorno,
                )
            )
        except PasarelaNoDisponible:
            # Estado desconocido: el pago queda PENDIENTE hasta recibir la confirmación.
            logger.warning("Pasarela no disponible para el pago %s", pago.pago_id)
            raise

        return self._aplicar(pago, resultado), False

    def consultar(self, pago_id: str, cliente_id: str) -> Pago:
        pago = self._pagos.obtener(pago_id)
        if pago is None or pago.cliente_id != cliente_id:
            raise PagoNoEncontrado(pago_id)
        return pago

    def consultar_por_referencia(self, referencia_pasarela: str) -> Pago:
        """Consulta usada por el portal PSE simulado; no expone datos a un cliente."""
        pago = self._pagos.obtener_por_referencia(referencia_pasarela)
        if pago is None:
            raise PagoNoEncontrado(referencia_pasarela)
        return pago

    def listar(self, cliente_id: str) -> list[Pago]:
        return self._pagos.listar_de_cliente(cliente_id)

    def confirmar(
        self,
        cuerpo: bytes,
        firma: str | None,
        referencia_pasarela: str,
        estado: EstadoPago,
        motivo: str | None = None,
    ) -> Pago:
        """Recibe la confirmación asíncrona de la pasarela (webhook) de forma idempotente."""

        esperada = firmar(cuerpo, secreto_webhook())
        if not firma or not hmac.compare_digest(esperada, firma):
            raise FirmaInvalida()

        pago = self._pagos.obtener_por_referencia(referencia_pasarela)
        if pago is None:
            raise PagoNoEncontrado(referencia_pasarela)
        if pago.estado.es_final:
            if pago.estado is not estado:
                logger.error(
                    "Confirmación contradictoria para %s: %s -> %s ignorada",
                    pago.pago_id,
                    pago.estado,
                    estado,
                )
            return pago
        return self._aplicar(
            pago,
            ResultadoCobro(referencia_pasarela, estado, motivo_rechazo=motivo),
        )

    @staticmethod
    def _reproducir(previo: Pago, huella: str) -> Pago:
        if not hmac.compare_digest(previo.huella_solicitud, huella):
            raise LlaveIdempotenciaReutilizada()
        return previo

    @staticmethod
    def _validar_medio(solicitud: SolicitudPago) -> None:
        if solicitud.metodo is MetodoPago.TARJETA and not solicitud.token_tarjeta:
            raise CotizacionNoPagable("TOKEN_REQUERIDO")
        if solicitud.metodo is MetodoPago.PSE and not solicitud.codigo_banco:
            raise CotizacionNoPagable("BANCO_REQUERIDO")

    def _aplicar(self, pago: Pago, resultado: ResultadoCobro) -> Pago:
        actualizado = pago.model_copy(
            update={
                "estado": resultado.estado,
                "referencia_pasarela": resultado.referencia_pasarela,
                "url_redireccion": resultado.url_redireccion,
                "motivo_rechazo": resultado.motivo_rechazo,
                "actualizado_en": self._reloj(),
            }
        )
        self._pagos.guardar(actualizado)
        if resultado.estado is EstadoPago.APROBADO:
            cotizacion = self._cotizaciones.obtener(pago.cotizacion_id)
            if cotizacion is not None and cotizacion.estado is EstadoCotizacion.VIGENTE:
                self._cotizaciones.guardar(
                    cotizacion.model_copy(update={"estado": EstadoCotizacion.ACEPTADA})
                )
        return actualizado
