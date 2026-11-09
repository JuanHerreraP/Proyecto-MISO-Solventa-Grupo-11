"""Entorno en memoria para probar la emisión de la póliza y su documento (HU12)."""

from dataclasses import dataclass

from app.cotizaciones.repositorio import RepositorioCotizacionesEnMemoria
from app.firmas.modelos import CanalOtp
from app.firmas.proveedor_simulado import ProveedorFirmaSimulado
from app.firmas.repositorio import RepositorioFirmasEnMemoria
from app.firmas.servicio import ServicioFirmas
from app.pagos.repositorio import RepositorioPagosEnMemoria
from app.polizas.almacenamiento import AlmacenEnMemoria
from app.polizas.comunicaciones import ComunicacionesSimuladas
from app.polizas.emision import ServicioEmision
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from app.polizas.repositorio_documentos import RepositorioDocumentosEnMemoria
from tests.firmas.fabrica import (
    CLIENTE,
    COTIZACION,
    SECRETO,
    Reloj,
    TitularesEnMemoria,
    cotizacion,
    pago,
)


@dataclass
class Entorno:
    firmas_servicio: ServicioFirmas
    emision: ServicioEmision
    firmas: RepositorioFirmasEnMemoria
    polizas: RepositorioPolizasEnMemoria
    documentos: RepositorioDocumentosEnMemoria
    almacen: AlmacenEnMemoria
    comunicaciones: ComunicacionesSimuladas
    proveedor: ProveedorFirmaSimulado
    cotizaciones: RepositorioCotizacionesEnMemoria
    reloj: Reloj

    @property
    def ultimo_codigo(self) -> str:
        return self.proveedor.ultimo_codigo or ""

    def firmar(self, cliente_id: str = CLIENTE, cotizacion_id: str = COTIZACION):
        """Recorre el flujo completo: presenta, pide el OTP y firma."""
        proceso = self.firmas_servicio.presentar(cliente_id, cotizacion_id)
        self.firmas_servicio.solicitar_otp(cliente_id, cotizacion_id, CanalOtp.SMS)
        return self.firmas_servicio.firmar(
            cliente_id,
            cotizacion_id,
            self.ultimo_codigo,
            proceso.huella_documento,
            ip="10.0.0.1",
            user_agent="pruebas",
        )


def crear_entorno() -> Entorno:
    firmas = RepositorioFirmasEnMemoria()
    cotizaciones = RepositorioCotizacionesEnMemoria()
    pagos = RepositorioPagosEnMemoria()
    polizas = RepositorioPolizasEnMemoria()
    documentos = RepositorioDocumentosEnMemoria()
    almacen = AlmacenEnMemoria()
    comunicaciones = ComunicacionesSimuladas()
    proveedor = ProveedorFirmaSimulado()
    reloj = Reloj()
    cotizaciones.guardar(cotizacion())
    pagos.crear(pago())

    emision = ServicioEmision(
        polizas=polizas,
        documentos=documentos,
        firmas=firmas,
        cotizaciones=cotizaciones,
        almacen=almacen,
        correo=comunicaciones,
        notificador=comunicaciones,
        reloj=reloj,
        generar_codigo=lambda: "abcdef0123456789",
    )
    secuencia = iter(f"{n:06d}" for n in range(123456, 999999, 111111))
    firmas_servicio = ServicioFirmas(
        firmas=firmas,
        cotizaciones=cotizaciones,
        pagos=pagos,
        titulares=TitularesEnMemoria(),
        proveedor=proveedor,
        secreto=SECRETO,
        reloj=reloj,
        generar_id=lambda: "FIR-0001",
        generar_codigo=lambda: next(secuencia),
        emisor=emision,
    )
    return Entorno(
        firmas_servicio,
        emision,
        firmas,
        polizas,
        documentos,
        almacen,
        comunicaciones,
        proveedor,
        cotizaciones,
        reloj,
    )
