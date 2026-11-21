"""Entorno en memoria para probar la renovación automática (HU17).

Reutiliza la fábrica de HU22: póliza de vida que cubre todo 2026 (prima 150.000) cuya
renovación cuesta 420.000 y cubre todo 2027. El preaviso se envía desde el 1 de diciembre
(30 días antes) y el cobro es el 31 de diciembre, último día de la vigencia.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time

from app.polizas.almacenamiento import AlmacenEnMemoria
from app.polizas.comunicaciones import CorreoRenovacionSimulado
from app.polizas.directorio_correos import DirectorioCorreosEnMemoria
from app.polizas.dominio.renovacion_automatica import (
    MedioPagoRegistrado,
    PreferenciaRenovacionAutomatica,
    ResultadoEjecucion,
)
from app.polizas.renovacion_automatica import ServicioRenovacionAutomatica
from app.polizas.repositorio_renovacion_automatica import (
    RepositorioCiclosEnMemoria,
    RepositorioPreferenciasEnMemoria,
)
from tests.renovaciones.fabrica import CLIENTE, POLIZA, TITULAR, Entorno, crear_entorno

CORREO = "laura@example.com"
INICIO_PREAVISO = date(2026, 12, 1)
VENCIMIENTO = date(2026, 12, 31)
TARJETA = MedioPagoRegistrado(token_tarjeta="tok_visa_aprobado_4242", ultimos_digitos="4242")
RECHAZADA = MedioPagoRegistrado(token_tarjeta="tok_rechazado_0002", ultimos_digitos="0002")
CAIDA = MedioPagoRegistrado(token_tarjeta="tok_caido_0003", ultimos_digitos="0003")

__all__ = ["CLIENTE", "POLIZA", "TITULAR"]


def a_las_10(dia: date) -> datetime:
    """Las 10 a. m. en Bogotá (15:00 UTC) del día indicado."""
    return datetime.combine(dia, time(15, 0), tzinfo=UTC)


@dataclass
class EntornoAutomatico:
    base: Entorno
    servicio: ServicioRenovacionAutomatica
    preferencias: RepositorioPreferenciasEnMemoria
    ciclos: RepositorioCiclosEnMemoria
    almacen: AlmacenEnMemoria
    correo: CorreoRenovacionSimulado
    directorio: DirectorioCorreosEnMemoria

    def ejecutar_el(self, dia: date) -> ResultadoEjecucion:
        self.base.reloj.ahora = a_las_10(dia)
        return self.servicio.ejecutar()

    def registrar(self, medio: MedioPagoRegistrado | None = TARJETA, activa: bool = True):
        self.preferencias.guardar(
            PreferenciaRenovacionAutomatica(poliza_id=POLIZA, activa=activa, medio_pago=medio)
        )

    def poliza(self):
        return self.base.polizas.obtener(POLIZA)

    def ciclo(self):
        ciclos = self.ciclos.por_poliza(POLIZA)
        return ciclos[0] if ciclos else None


def crear_entorno_automatico(con_correo: bool = True, **opciones) -> EntornoAutomatico:
    base = crear_entorno(**opciones)
    preferencias = RepositorioPreferenciasEnMemoria()
    ciclos = RepositorioCiclosEnMemoria()
    almacen = AlmacenEnMemoria()
    correo = CorreoRenovacionSimulado()
    directorio = DirectorioCorreosEnMemoria({CLIENTE: CORREO} if con_correo else {})
    servicio = ServicioRenovacionAutomatica(
        polizas=base.polizas,
        cotizaciones=base.cotizaciones,
        preferencias=preferencias,
        ciclos=ciclos,
        renovaciones=base.renovaciones,
        servicio_renovaciones=base.servicio,
        pagos=base.pagos,
        servicio_pagos=base.pagos_servicio,
        almacen=almacen,
        correo=correo,
        directorio=directorio,
        reloj=base.reloj,
    )
    return EntornoAutomatico(base, servicio, preferencias, ciclos, almacen, correo, directorio)
