"""Entorno en memoria para probar la evaluación de siniestros y el desembolso (HU15)."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal

from app.desembolsos.modelos import SolicitudCuenta, TipoCuenta
from app.desembolsos.puertos import RedNoDisponible
from app.desembolsos.red_simulada import RedDesembolsosSimulada
from app.desembolsos.repositorio import (
    RepositorioCuentasEnMemoria,
    RepositorioDesembolsosEnMemoria,
)
from app.desembolsos.servicio import ServicioDesembolsos
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from app.siniestros.evaluacion import ServicioEvaluacion
from app.siniestros.modelos import EstadoSiniestro, OrigenSiniestro, Siniestro
from app.siniestros.repositorio import RepositorioSiniestrosEnMemoria
from tests.billetera.fabrica import poliza

# 2026-10-21 10:00 en Bogotá. La póliza de la fábrica asegura $40.000.000.
AHORA = datetime(2026, 10, 21, 15, 0, tzinfo=UTC)
CLIENTE = "CLI-001"
OPERADOR = "OPE-1"


def siniestro(**cambios) -> Siniestro:
    datos = {
        "siniestro_id": "SIN-1",
        "cliente_id": CLIENTE,
        "poliza_id": "POL-1",
        "origen": OrigenSiniestro.MANUAL,
        "estado": EstadoSiniestro.REGISTRADO,
        "fecha_evento": date(2026, 10, 20),
        "hora_evento": time(18, 30),
        "lugar": "Aeropuerto El Dorado",
        "descripcion": "El vuelo fue cancelado y hubo gastos adicionales.",
        "estimacion_danos": Decimal("850000.00"),
        "registrado_por": CLIENTE,
        "registrado_en": datetime(2026, 10, 20, 23, 0, tzinfo=UTC),
    }
    datos.update(cambios)
    return Siniestro(**datos)


def cuenta(numero: str = "12345678") -> SolicitudCuenta:
    return SolicitudCuenta(
        codigo_banco="1007", tipo_cuenta=TipoCuenta.AHORROS, numero_cuenta=numero
    )


class RedContadora(RedDesembolsosSimulada):
    """La red simulada, contando las órdenes y pudiendo caerse a voluntad."""

    def __init__(self):
        self.transferencias: list[str] = []
        self.retiros: list[str] = []
        self.caida = False

    def transferir(self, transferencia):
        if self.caida:
            raise RedNoDisponible("caída")
        self.transferencias.append(transferencia.referencia_interna)
        return super().transferir(transferencia)

    def emitir_codigo_retiro(self, orden):
        if self.caida:
            raise RedNoDisponible("caída")
        self.retiros.append(orden.referencia_interna)
        return super().emitir_codigo_retiro(orden)


@dataclass
class Entorno:
    evaluacion: ServicioEvaluacion
    desembolsos: ServicioDesembolsos
    siniestros: RepositorioSiniestrosEnMemoria
    polizas: RepositorioPolizasEnMemoria
    repo_desembolsos: RepositorioDesembolsosEnMemoria
    cuentas: RepositorioCuentasEnMemoria
    red: RedContadora


def crear_entorno(*siniestros: Siniestro) -> Entorno:
    polizas = RepositorioPolizasEnMemoria()
    polizas.guardar(poliza())
    repo_siniestros = RepositorioSiniestrosEnMemoria()
    for s in siniestros or (siniestro(),):
        repo_siniestros.guardar(s)
    repo_desembolsos = RepositorioDesembolsosEnMemoria()
    cuentas = RepositorioCuentasEnMemoria()
    red = RedContadora()
    contador = iter(range(1, 1000))
    desembolsos = ServicioDesembolsos(
        repo_desembolsos,
        cuentas,
        red,
        reloj=lambda: AHORA,
        generar_id=lambda: f"DES-{next(contador)}",
    )
    evaluacion = ServicioEvaluacion(repo_siniestros, polizas, desembolsos, reloj=lambda: AHORA)
    return Entorno(
        evaluacion, desembolsos, repo_siniestros, polizas, repo_desembolsos, cuentas, red
    )
