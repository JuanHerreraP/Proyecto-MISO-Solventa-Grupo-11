"""Caso de uso: listar las primas pendientes de pago del cliente (HU21).

Junta tres cosas que el cliente debe resolver para tener su cobertura al día: las renovaciones
iniciadas sin pagar, las cotizaciones vigentes sin pagar y los contratos pagados sin firmar.
Todo se arma con los datos que ya existen, sin tablas nuevas.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from app.cotizaciones.dominio.modelos import Cotizacion, EstadoCotizacion
from app.cotizaciones.repositorio import RepositorioCotizaciones
from app.firmas.contrato import nombre_ramo_de
from app.firmas.modelos import EstadoFirma
from app.firmas.puertos import RepositorioFirmas
from app.pagos.modelos import EstadoPago, Pago
from app.pagos.puertos import RepositorioPagos
from app.polizas.dominio.modelos import EstadoRegistroPoliza, Poliza
from app.polizas.dominio.primas_pendientes import (
    MENSAJE_FIRMA_PENDIENTE,
    AccionPrima,
    PrimaPendiente,
    PrimasPendientes,
    TipoPrimaPendiente,
    fin_de_vigencia,
    ordenar_por_fecha_limite,
)
from app.polizas.dominio.renovacion import EstadoRenovacion, Renovacion
from app.polizas.repositorio import RepositorioPolizas
from app.polizas.repositorio_renovaciones import RepositorioRenovaciones

logger = logging.getLogger(__name__)


class ServicioPrimasPendientes:
    def __init__(
        self,
        cotizaciones: RepositorioCotizaciones,
        pagos: RepositorioPagos,
        polizas: RepositorioPolizas,
        renovaciones: RepositorioRenovaciones,
        firmas: RepositorioFirmas,
        aplicar_pago: Callable[[Pago], None] | None = None,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self._cotizaciones = cotizaciones
        self._pagos = pagos
        self._polizas = polizas
        self._renovaciones = renovaciones
        self._firmas = firmas
        self._aplicar_pago = aplicar_pago
        self._reloj = reloj

    def listar(self, cliente_id: str) -> PrimasPendientes:
        ahora = self._reloj()
        cotizaciones = self._cotizaciones.listar_por_cliente(cliente_id)
        polizas = self._polizas.listar_por_cliente(cliente_id)
        aprobados = {
            p.cotizacion_id: p
            for p in self._pagos.listar_de_cliente(cliente_id)
            if p.estado is EstadoPago.APROBADO
        }
        renovaciones = self._renovaciones_de(polizas)
        con_poliza = {p.cotizacion_id for p in polizas if p.cotizacion_id}
        por_id = {c.cotizacion_id: c for c in cotizaciones}

        primas: list[PrimaPendiente] = []
        for cotizacion_id, (poliza, renovacion) in renovaciones.items():
            prima = self._de_renovacion(
                poliza, renovacion, por_id.get(cotizacion_id), aprobados.get(cotizacion_id), ahora
            )
            if prima is not None:
                primas.append(prima)

        for cotizacion in cotizaciones:
            # Las cotizaciones de una renovación ya se trataron arriba: no se repiten.
            if cotizacion.cotizacion_id in renovaciones:
                continue
            pago = aprobados.get(cotizacion.cotizacion_id)
            if pago is None:
                prima = self._de_cotizacion(cotizacion, ahora)
            elif cotizacion.cotizacion_id not in con_poliza:
                prima = self._de_firma_pendiente(cotizacion, pago)
            else:
                prima = None
            if prima is not None:
                primas.append(prima)

        ordenadas = ordenar_por_fecha_limite(primas)
        return PrimasPendientes(primas=tuple(ordenadas), total=len(ordenadas))

    def _renovaciones_de(self, polizas: list[Poliza]) -> dict[str, tuple[Poliza, Renovacion]]:
        """Las renovaciones del cliente, por cotización, con la póliza que renuevan."""
        resultado: dict[str, tuple[Poliza, Renovacion]] = {}
        for poliza in polizas:
            for renovacion in self._renovaciones.por_poliza(poliza.poliza_id):
                resultado[renovacion.cotizacion_id] = (poliza, renovacion)
        return resultado

    def _de_renovacion(
        self,
        poliza: Poliza,
        renovacion: Renovacion,
        cotizacion: Cotizacion | None,
        pago: Pago | None,
        ahora: datetime,
    ) -> PrimaPendiente | None:
        if renovacion.estado is not EstadoRenovacion.PENDIENTE_PAGO:
            return None
        if pago is not None:
            # Ya se pagó: el aviso del pago pudo fallar. Se aplica ahora y no se lista.
            self._aplicar(pago)
            return None
        if not renovacion.pendiente_en(ahora) or poliza.estado is EstadoRegistroPoliza.CANCELADA:
            return None
        if cotizacion is None:
            logger.error("La renovación %s no tiene cotización", renovacion.renovacion_id)
            return None
        # El cliente paga antes de que venza la cotización y, en todo caso, antes de que
        # termine la póliza que renueva.
        limite = min(renovacion.vigente_hasta, fin_de_vigencia(renovacion.anterior_fin))
        return PrimaPendiente(
            tipo=TipoPrimaPendiente.RENOVACION,
            accion=AccionPrima.PAGAR,
            referencia_id=renovacion.renovacion_id,
            cotizacion_id=renovacion.cotizacion_id,
            poliza_id=poliza.poliza_id,
            numero_poliza=poliza.numero_poliza,
            ramo=cotizacion.ramo.value,
            nombre_ramo=nombre_ramo_de(cotizacion.ramo, cotizacion.datos_riesgo),
            monto=renovacion.prima_total,
            moneda=renovacion.moneda,
            fecha_limite=limite,
        )

    @staticmethod
    def _de_cotizacion(cotizacion: Cotizacion, ahora: datetime) -> PrimaPendiente | None:
        if cotizacion.estado_en(ahora) is not EstadoCotizacion.VIGENTE:
            return None
        return PrimaPendiente(
            tipo=TipoPrimaPendiente.COTIZACION,
            accion=AccionPrima.PAGAR,
            referencia_id=cotizacion.cotizacion_id,
            cotizacion_id=cotizacion.cotizacion_id,
            ramo=cotizacion.ramo.value,
            nombre_ramo=nombre_ramo_de(cotizacion.ramo, cotizacion.datos_riesgo),
            monto=cotizacion.prima_total,
            moneda=cotizacion.moneda,
            fecha_limite=cotizacion.vigente_hasta,
        )

    def _de_firma_pendiente(self, cotizacion: Cotizacion, pago: Pago) -> PrimaPendiente | None:
        proceso = self._firmas.obtener_por_cotizacion(cotizacion.cotizacion_id)
        if proceso is not None and proceso.estado is EstadoFirma.FIRMADA:
            # Ya firmó: la póliza se emite al consultar el contrato. No hay nada que pedirle.
            return None
        return PrimaPendiente(
            tipo=TipoPrimaPendiente.FIRMA_PENDIENTE,
            accion=AccionPrima.FIRMAR,
            referencia_id=cotizacion.cotizacion_id,
            cotizacion_id=cotizacion.cotizacion_id,
            ramo=cotizacion.ramo.value,
            nombre_ramo=nombre_ramo_de(cotizacion.ramo, cotizacion.datos_riesgo),
            monto=pago.monto,
            moneda=pago.moneda,
            mensaje=MENSAJE_FIRMA_PENDIENTE,
        )

    def _aplicar(self, pago: Pago) -> None:
        if self._aplicar_pago is None:
            return
        try:
            self._aplicar_pago(pago)
        except Exception:
            logger.exception("No se pudo aplicar el pago aprobado %s", pago.pago_id)
