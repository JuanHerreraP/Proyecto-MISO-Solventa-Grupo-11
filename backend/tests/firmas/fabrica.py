"""Datos y dobles compartidos por las pruebas de firma (HU14 / BPM-60)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.cotizaciones.dominio.modelos import (
    CoberturaPrincipal,
    Cotizacion,
    EstadoCotizacion,
    RamoSeguro,
)
from app.cotizaciones.repositorio import RepositorioCotizacionesEnMemoria
from app.firmas.contrato import TitularContrato
from app.firmas.proveedor_simulado import ProveedorFirmaSimulado
from app.firmas.repositorio import RepositorioFirmasEnMemoria
from app.firmas.servicio import ServicioFirmas
from app.pagos.modelos import EstadoPago, MetodoPago, Pago
from app.pagos.repositorio import RepositorioPagosEnMemoria

AHORA = datetime(2027, 1, 1, 15, 0, tzinfo=UTC)
CLIENTE = "CLI-001"
COTIZACION = "COT-001"
SECRETO = b"secreto-otp-de-pruebas"


def cotizacion(cliente=CLIENTE, cot_id=COTIZACION, estado=EstadoCotizacion.ACEPTADA) -> Cotizacion:
    return Cotizacion(
        cotizacion_id=cot_id,
        cliente_id=cliente,
        ramo=RamoSeguro.VIDA,
        datos_riesgo={"valor_credito": 250000000, "plazo_meses": 240},
        estado=estado,
        prima_total=Decimal("94500.00"),
        cobertura_principal=CoberturaPrincipal(
            codigo="VIDA_DEUDORES",
            nombre="Vida deudores hipotecario",
            suma_asegurada=Decimal("250000000.00"),
        ),
        creada_en=AHORA - timedelta(hours=1),
        vigente_hasta=AHORA + timedelta(days=7),
    )


def pago(cliente=CLIENTE, cot_id=COTIZACION, estado=EstadoPago.APROBADO) -> Pago:
    return Pago(
        pago_id=f"PAG-{cot_id}",
        cotizacion_id=cot_id,
        cliente_id=cliente,
        idempotency_key=f"llave-{cot_id}",
        huella_solicitud="a" * 64,
        metodo=MetodoPago.TARJETA,
        monto=Decimal("94500.00"),
        moneda="COP",
        estado=estado,
        referencia_pasarela=f"PSP-{cot_id}",
        creado_en=AHORA - timedelta(minutes=5),
        actualizado_en=AHORA - timedelta(minutes=4),
    )


class TitularesEnMemoria:
    def __init__(self):
        self.por_cliente: dict[str, TitularContrato] = {
            CLIENTE: TitularContrato(
                nombre_completo="Laura Gómez",
                tipo_documento="CC",
                numero_documento="1020304050",
                email="laura@example.com",
                celular="+57 300 123 4567",
            )
        }

    def obtener(self, cliente_id: str) -> TitularContrato | None:
        return self.por_cliente.get(cliente_id)


class Reloj:
    def __init__(self, ahora: datetime = AHORA):
        self.ahora = ahora

    def __call__(self) -> datetime:
        return self.ahora

    def avanzar(self, **delta) -> None:
        self.ahora += timedelta(**delta)


@dataclass
class Entorno:
    servicio: ServicioFirmas
    firmas: RepositorioFirmasEnMemoria
    cotizaciones: RepositorioCotizacionesEnMemoria
    pagos: RepositorioPagosEnMemoria
    titulares: TitularesEnMemoria
    proveedor: ProveedorFirmaSimulado
    reloj: Reloj

    @property
    def ultimo_codigo(self) -> str:
        return self.proveedor.ultimo_codigo or ""


def crear_entorno() -> Entorno:
    firmas = RepositorioFirmasEnMemoria()
    cotizaciones = RepositorioCotizacionesEnMemoria()
    pagos = RepositorioPagosEnMemoria()
    titulares = TitularesEnMemoria()
    proveedor = ProveedorFirmaSimulado()
    reloj = Reloj()
    cotizaciones.guardar(cotizacion())
    pagos.crear(pago())
    secuencia = iter(f"{n:06d}" for n in range(123456, 999999, 111111))
    servicio = ServicioFirmas(
        firmas=firmas,
        cotizaciones=cotizaciones,
        pagos=pagos,
        titulares=titulares,
        proveedor=proveedor,
        secreto=SECRETO,
        reloj=reloj,
        generar_id=lambda: "FIR-0001",
        generar_codigo=lambda: next(secuencia),
    )
    return Entorno(servicio, firmas, cotizaciones, pagos, titulares, proveedor, reloj)
