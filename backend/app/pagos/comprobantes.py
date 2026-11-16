"""Comprobante de un pago aprobado (HU21).

Se genera cuando el pago queda aprobado y el cliente lo consulta para verlo en pantalla. Es un
registro propio, inmutable e idempotente: un pago tiene un solo comprobante, aunque el aviso del
pago llegue dos veces o falle y se recupere al consultarlo.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from app.cotizaciones.repositorio import RepositorioCotizaciones
from app.firmas.contrato import nombre_ramo_de
from app.pagos.modelos import Comprobante, ConceptoComprobante, EstadoPago, Pago
from app.pagos.repositorio_comprobantes import RepositorioComprobantes
from app.polizas.dominio.modelos import hoy_en_colombia
from app.polizas.repositorio import RepositorioPolizas
from app.polizas.repositorio_renovaciones import RepositorioRenovaciones

logger = logging.getLogger(__name__)


class PagoSinComprobante(Exception):
    """Solo un pago aprobado tiene comprobante."""


def numero_de(pago: Pago) -> str:
    """Número legible y estable: la fecha del pago (Bogotá) y el final de su identificador."""
    fecha = hoy_en_colombia(pago.actualizado_en)
    return f"CP-{fecha:%Y%m%d}-{pago.pago_id[-8:].upper()}"


class ServicioComprobantes:
    def __init__(
        self,
        comprobantes: RepositorioComprobantes,
        cotizaciones: RepositorioCotizaciones,
        renovaciones: RepositorioRenovaciones,
        polizas: RepositorioPolizas,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self._comprobantes = comprobantes
        self._cotizaciones = cotizaciones
        self._renovaciones = renovaciones
        self._polizas = polizas
        self._reloj = reloj

    def concepto_de(self, cotizacion_id: str) -> ConceptoComprobante:
        """Renovación si la cotización la creó una renovación; compra en cualquier otro caso."""
        if self._renovaciones.por_cotizacion(cotizacion_id) is not None:
            return ConceptoComprobante.RENOVACION
        return ConceptoComprobante.COMPRA

    def emitir(self, pago: Pago) -> Comprobante | None:
        """Genera el comprobante del pago aprobado. Repetirlo devuelve el mismo."""
        if pago.estado is not EstadoPago.APROBADO:
            return None
        existente = self._comprobantes.por_pago(pago.pago_id)
        if existente is not None:
            return existente

        comprobante = self._armar(pago)
        if self._comprobantes.crear(comprobante):
            return comprobante
        # Otra solicitud lo creó entre la consulta y la inserción.
        return self._comprobantes.por_pago(pago.pago_id)

    def obtener(self, pago: Pago) -> Comprobante:
        """El comprobante del pago; si el aviso del pago falló, se genera ahora."""
        if pago.estado is not EstadoPago.APROBADO:
            raise PagoSinComprobante(pago.pago_id)
        comprobante = self.emitir(pago)
        if comprobante is None:  # pragma: no cover - emitir solo devuelve None si no se aprobó
            raise PagoSinComprobante(pago.pago_id)
        return comprobante

    def _armar(self, pago: Pago) -> Comprobante:
        cotizacion = self._cotizaciones.obtener(pago.cotizacion_id)
        if cotizacion is None:
            logger.error("El pago %s no tiene cotización", pago.pago_id)
            nombre_ramo = "Seguro"
        else:
            nombre_ramo = nombre_ramo_de(cotizacion.ramo, cotizacion.datos_riesgo)

        concepto = ConceptoComprobante.COMPRA
        descripcion = f"Prima de {nombre_ramo}"
        poliza_id = numero_poliza = None
        renovacion = self._renovaciones.por_cotizacion(pago.cotizacion_id)
        if renovacion is not None:
            concepto = ConceptoComprobante.RENOVACION
            poliza = self._polizas.obtener(renovacion.poliza_id)
            poliza_id = renovacion.poliza_id
            numero_poliza = poliza.numero_poliza if poliza is not None else None
            referencia = f" {numero_poliza}" if numero_poliza else ""
            descripcion = f"Renovación de la póliza{referencia} ({nombre_ramo})"

        return Comprobante(
            comprobante_id=f"CMP-{pago.pago_id}",
            numero=numero_de(pago),
            pago_id=pago.pago_id,
            cliente_id=pago.cliente_id,
            cotizacion_id=pago.cotizacion_id,
            concepto=concepto,
            descripcion=descripcion,
            poliza_id=poliza_id,
            numero_poliza=numero_poliza,
            nombre_ramo=nombre_ramo,
            monto=pago.monto,
            moneda=pago.moneda,
            metodo=pago.metodo,
            referencia_pasarela=pago.referencia_pasarela,
            pagado_en=pago.actualizado_en,
            emitido_en=self._reloj(),
        )
