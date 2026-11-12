"""Entorno en memoria para probar las primas pendientes (HU21).

Parte del entorno de renovaciones: una póliza de vida vigente todo 2026 y hoy es 10 de diciembre
(dentro de la ventana de renovación). La cotización original de la póliza ya está aceptada.
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from app.cotizaciones.dominio.modelos import (
    CoberturaPrincipal,
    Cotizacion,
    EstadoCotizacion,
    RamoSeguro,
)
from app.firmas.modelos import EstadoFirma
from app.pagos.modelos import EstadoPago, MetodoPago, Pago
from app.polizas.primas_pendientes import ServicioPrimasPendientes
from tests.renovaciones.fabrica import (
    AHORA,
    CLIENTE,
    COTIZACION,
    POLIZA,
    TITULAR,
    Entorno,
    crear_entorno,
)

__all__ = ["AHORA", "CLIENTE", "COTIZACION", "POLIZA", "TITULAR"]


class FirmasFalsas:
    """Solo responde lo que el servicio consulta: el estado de la firma de una cotización."""

    def __init__(self):
        self._estados: dict[str, EstadoFirma] = {}

    def firmar(self, cotizacion_id: str, estado: EstadoFirma = EstadoFirma.FIRMADA) -> None:
        self._estados[cotizacion_id] = estado

    def obtener_por_cotizacion(self, cotizacion_id: str):
        estado = self._estados.get(cotizacion_id)
        return None if estado is None else SimpleNamespace(estado=estado)


@dataclass
class EntornoPrimas:
    base: Entorno
    servicio: ServicioPrimasPendientes
    firmas: FirmasFalsas

    def listar(self, cliente_id: str = CLIENTE):
        return self.servicio.listar(cliente_id)

    def iniciar_renovacion(self):
        return self.base.servicio.iniciar(TITULAR, POLIZA, "k-1")[0]


def crear_entorno_primas(**cambios) -> EntornoPrimas:
    base = crear_entorno(**cambios)
    firmas = FirmasFalsas()
    servicio = ServicioPrimasPendientes(
        cotizaciones=base.cotizaciones,
        pagos=base.pagos,
        polizas=base.polizas,
        renovaciones=base.renovaciones,
        firmas=firmas,
        aplicar_pago=base.servicio.aplicar_pago,
        reloj=base.reloj,
    )
    return EntornoPrimas(base, servicio, firmas)


def cotizacion_vigente(
    cotizacion_id: str = "COT-NUEVA",
    cliente_id: str = CLIENTE,
    estado: EstadoCotizacion = EstadoCotizacion.VIGENTE,
    vigente_dias: int = 5,
) -> Cotizacion:
    return Cotizacion(
        cotizacion_id=cotizacion_id,
        cliente_id=cliente_id,
        ramo=RamoSeguro.VIDA,
        datos_riesgo={},
        estado=estado,
        prima_total=Decimal("89000.00"),
        cobertura_principal=CoberturaPrincipal(
            codigo="FALLECIMIENTO",
            nombre="Cobertura por fallecimiento",
            suma_asegurada=Decimal("50000000.00"),
        ),
        creada_en=AHORA - timedelta(hours=1),
        vigente_hasta=AHORA + timedelta(days=vigente_dias),
    )


def pago_aprobado(cotizacion_id: str, cliente_id: str = CLIENTE) -> Pago:
    return Pago(
        pago_id=f"PAG-{cotizacion_id}",
        cotizacion_id=cotizacion_id,
        cliente_id=cliente_id,
        idempotency_key=f"llave-{cotizacion_id}",
        huella_solicitud="a" * 64,
        metodo=MetodoPago.TARJETA,
        monto=Decimal("89000.00"),
        moneda="COP",
        estado=EstadoPago.APROBADO,
        referencia_pasarela=f"PSP-{cotizacion_id}",
        creado_en=AHORA - timedelta(minutes=5),
        actualizado_en=AHORA - timedelta(minutes=4),
    )
