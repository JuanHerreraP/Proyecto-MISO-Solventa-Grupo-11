"""Entorno en memoria para probar la renovación de pólizas (HU22).

La póliza de la fábrica es de vida, todo 2026 (365 días, prima 150.000), y hoy es 10 de diciembre:
está dentro de la ventana de 30 días antes del vencimiento. La renovación cubre todo 2027 y su
prima se recalcula con el rating: 100 millones x 0,00035 x 12 meses = 420.000.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.cotizaciones.repositorio import RepositorioCotizacionesEnMemoria
from app.cotizaciones.servicio_personalizacion import ServicioPersonalizacionCotizacion
from app.identidad.modelos import Rol
from app.pagos.modelos import MetodoPago, Pago, SolicitudPago
from app.pagos.pasarela_simulada import PasarelaSimulada
from app.pagos.repositorio import RepositorioPagosEnMemoria
from app.pagos.servicio import ServicioPagos
from app.perfilamiento.dominio.modelos import (
    ClasificacionRiesgo,
    Dictamen,
    OrigenSenales,
    PerfilRiesgo,
)
from app.perfilamiento.enriquecimiento.memoria import RepositorioConsentimientosEnMemoria
from app.perfilamiento.enriquecimiento.modelos import Consentimiento
from app.perfilamiento.repositorio import RepositorioPerfilesEnMemoria
from app.polizas.endosos import Solicitante
from app.polizas.renovacion import ServicioRenovaciones
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from app.polizas.repositorio_renovaciones import RepositorioRenovacionesEnMemoria
from tests.endosos.fabrica import CLIENTE, COTIZACION, POLIZA, cotizacion, poliza

# 2026-12-10 10:00 en Bogotá: a la póliza le quedan 21 días de vigencia.
AHORA = datetime(2026, 12, 10, 15, 0, tzinfo=UTC)
HOY = date(2026, 12, 10)
TITULAR = Solicitante(CLIENTE, Rol.CLIENTE, ip="10.0.0.1", user_agent="pytest")
ASESOR = Solicitante("ASE-1", Rol.ASESOR_VENTAS)
PRIMA_RENOVADA = Decimal("420000.00")

DATOS_VIDA = {
    "fecha_nacimiento": "1990-05-10",
    "valor_asegurado": "100000000",
    "meses_cobertura": 12,
    "fumador": False,
}

__all__ = ["CLIENTE", "COTIZACION", "POLIZA", "poliza"]


class Reloj:
    def __init__(self, ahora: datetime = AHORA):
        self.ahora = ahora

    def __call__(self) -> datetime:
        return self.ahora

    def avanzar(self, **delta) -> None:
        self.ahora += timedelta(**delta)


def perfil(dictamen: Dictamen = Dictamen.AJUSTADO, factor: float | None = 1.2) -> PerfilRiesgo:
    return PerfilRiesgo(
        perfil_id="PERFIL-001",
        cliente_id=CLIENTE,
        consentimiento_id="CONS-001",
        puntaje_riesgo=55,
        clasificacion=ClasificacionRiesgo.MEDIO,
        dictamen=dictamen,
        factor_riesgo=factor,
        extraprima_porcentaje=20,
        origen_senales=OrigenSenales.FUENTES_EXTERNAS,
        version_reglas="1.0.0",
        reglas_aplicadas=[],
        fecha_calculo=AHORA,
        tiempo_calculo_ms=10,
    )


def solicitud_pago(cotizacion_id: str, token: str = "tok_visa_aprobado") -> SolicitudPago:
    return SolicitudPago(
        cotizacion_id=cotizacion_id, metodo=MetodoPago.TARJETA, token_tarjeta=token
    )


@dataclass
class Entorno:
    servicio: ServicioRenovaciones
    pagos_servicio: ServicioPagos
    polizas: RepositorioPolizasEnMemoria
    renovaciones: RepositorioRenovacionesEnMemoria
    cotizaciones: RepositorioCotizacionesEnMemoria
    pagos: RepositorioPagosEnMemoria
    reloj: Reloj

    def pagar(
        self, cotizacion_id: str, llave: str = "llave-0001", token: str = "tok_visa_aprobado"
    ):
        return self.pagos_servicio.pagar(CLIENTE, llave, solicitud_pago(cotizacion_id, token))[0]


def crear_entorno(
    asesor_id: str | None = None,
    datos_riesgo: dict[str, object] | None = None,
    con_cotizacion: bool = True,
    perfil_riesgo: PerfilRiesgo | None = None,
    avisar_pagos: bool = True,
    **cambios_poliza,
) -> Entorno:
    polizas = RepositorioPolizasEnMemoria()
    polizas.guardar(poliza(**cambios_poliza))
    cotizaciones = RepositorioCotizacionesEnMemoria()
    if con_cotizacion:
        original = cotizacion(asesor_id)
        cotizaciones.guardar(
            original.model_copy(update={"datos_riesgo": datos_riesgo or DATOS_VIDA})
        )
    reloj = Reloj()

    perfiles = RepositorioPerfilesEnMemoria()
    consentimientos = RepositorioConsentimientosEnMemoria()
    if perfil_riesgo is not None:
        perfiles.guardar(perfil_riesgo)
        consentimientos.registrar(
            Consentimiento(
                consentimiento_id="CONS-001",
                cliente_id=CLIENTE,
                vence_en=AHORA + timedelta(days=30),
            )
        )
    personalizador = ServicioPersonalizacionCotizacion(perfiles, consentimientos, reloj=reloj)

    pagos = RepositorioPagosEnMemoria()
    renovaciones = RepositorioRenovacionesEnMemoria(polizas)
    servicio = ServicioRenovaciones(
        polizas, renovaciones, cotizaciones, personalizador, pagos, reloj=reloj
    )
    pagos_servicio = ServicioPagos(
        pagos,
        cotizaciones,
        PasarelaSimulada(url_base="http://pruebas"),
        reloj=reloj,
        al_aprobar=servicio.aplicar_pago if avisar_pagos else None,
    )
    return Entorno(servicio, pagos_servicio, polizas, renovaciones, cotizaciones, pagos, reloj)


def aprobado(pago: Pago) -> bool:
    return pago.estado.value == "APROBADO"
