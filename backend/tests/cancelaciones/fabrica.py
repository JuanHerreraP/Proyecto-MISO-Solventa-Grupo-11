"""Entorno en memoria para probar la cancelación de pólizas (HU22)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.cotizaciones.repositorio import RepositorioCotizacionesEnMemoria
from app.desembolsos.modelos import Desembolso, EstadoDesembolso, MedioDesembolso
from app.desembolsos.repositorio import RepositorioDesembolsosEnMemoria
from app.identidad.modelos import Rol
from app.polizas.cancelacion import ServicioCancelaciones
from app.polizas.dominio.cancelacion import MotivoCancelacion, SolicitudCancelacion
from app.polizas.endosos import Solicitante
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from app.polizas.repositorio_cancelaciones import RepositorioCancelacionesEnMemoria
from app.siniestros.modelos import EstadoSiniestro
from app.siniestros.repositorio import RepositorioSiniestrosEnMemoria
from tests.desembolsos.fabrica import siniestro as _siniestro
from tests.endosos.fabrica import AHORA, CLIENTE, HOY, POLIZA, cotizacion, poliza

TITULAR = Solicitante(CLIENTE, Rol.CLIENTE, ip="10.0.0.1", user_agent="pytest")
ASESOR = Solicitante("ASE-1", Rol.ASESOR_VENTAS)

__all__ = ["AHORA", "CLIENTE", "HOY", "POLIZA", "Entorno", "crear_entorno", "poliza"]


class Reloj:
    def __init__(self, ahora: datetime = AHORA):
        self.ahora = ahora

    def __call__(self) -> datetime:
        return self.ahora

    def avanzar(self, **delta) -> None:
        self.ahora += timedelta(**delta)


def solicitud(
    motivo: MotivoCancelacion = MotivoCancelacion.YA_NO_LA_NECESITO,
    confirmo: bool = True,
    detalle: str | None = None,
) -> SolicitudCancelacion:
    return SolicitudCancelacion(motivo=motivo, confirmo=confirmo, detalle=detalle)


def siniestro(estado: EstadoSiniestro, siniestro_id: str = "SIN-1"):
    return _siniestro(
        siniestro_id=siniestro_id, poliza_id=POLIZA, cliente_id=CLIENTE, estado=estado
    )


def desembolso(estado: EstadoDesembolso, siniestro_id: str = "SIN-1") -> Desembolso:
    return Desembolso(
        desembolso_id=f"DES-{siniestro_id}",
        siniestro_id=siniestro_id,
        poliza_id=POLIZA,
        cliente_id=CLIENTE,
        monto=Decimal("850000.00"),
        moneda="COP",
        medio=MedioDesembolso.CUENTA_BANCARIA,
        estado=estado,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )


@dataclass
class Entorno:
    servicio: ServicioCancelaciones
    polizas: RepositorioPolizasEnMemoria
    cancelaciones: RepositorioCancelacionesEnMemoria
    siniestros: RepositorioSiniestrosEnMemoria
    desembolsos: RepositorioDesembolsosEnMemoria
    reloj: Reloj


def crear_entorno(asesor_id: str | None = None, **cambios_poliza) -> Entorno:
    polizas = RepositorioPolizasEnMemoria()
    polizas.guardar(poliza(**cambios_poliza))
    cancelaciones = RepositorioCancelacionesEnMemoria(polizas)
    siniestros = RepositorioSiniestrosEnMemoria()
    desembolsos = RepositorioDesembolsosEnMemoria()
    cotizaciones = RepositorioCotizacionesEnMemoria()
    cotizaciones.guardar(cotizacion(asesor_id))
    reloj = Reloj()
    servicio = ServicioCancelaciones(
        polizas=polizas,
        cancelaciones=cancelaciones,
        siniestros=siniestros,
        desembolsos=desembolsos,
        cotizaciones=cotizaciones,
        reloj=reloj,
    )
    return Entorno(servicio, polizas, cancelaciones, siniestros, desembolsos, reloj)


__all__ += ["ASESOR", "TITULAR", "UTC", "desembolso", "siniestro", "solicitud"]
