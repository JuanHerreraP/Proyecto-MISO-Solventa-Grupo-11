"""Pólizas y entorno en memoria para probar los endosos (HU16)."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.cotizaciones.dominio.modelos import (
    CoberturaPrincipal,
    Cotizacion,
    EstadoCotizacion,
    RamoSeguro,
)
from app.cotizaciones.repositorio import RepositorioCotizacionesEnMemoria
from app.polizas.almacenamiento import AlmacenEnMemoria
from app.polizas.dominio.endosos import CoberturaSolicitada, SolicitudModificacion
from app.polizas.dominio.modelos import Beneficiario, CoberturaPoliza, Poliza, RamoPoliza
from app.polizas.endosos import ServicioEndosos
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from app.polizas.repositorio_endosos import RepositorioEndososEnMemoria

# 2026-07-02 10:00 en Bogotá. A la póliza de vida (todo 2026) le quedan 183 de 365 días.
AHORA = datetime(2026, 7, 2, 15, 0, tzinfo=UTC)
HOY = date(2026, 7, 2)
CLIENTE = "CLI-001"
POLIZA = "POL-VIDA-1"
COTIZACION = "COT-VIDA-1"


def poliza(**cambios) -> Poliza:
    datos = {
        "poliza_id": POLIZA,
        "numero_poliza": "SOL-2026-VIDA0001",
        "cliente_id": CLIENTE,
        "cotizacion_id": COTIZACION,
        "ramo": RamoPoliza.VIDA,
        "titular_nombre": "Laura Gómez",
        "titular_tipo_documento": "CC",
        "titular_numero_documento": "1012345678",
        "fecha_inicio": date(2026, 1, 1),
        "fecha_fin": date(2026, 12, 31),
        "prima_total": Decimal("150000.00"),
        "cobertura_principal": CoberturaPoliza(
            codigo="FALLECIMIENTO",
            nombre="Cobertura por fallecimiento",
            suma_asegurada=Decimal("100000000.00"),
        ),
        "codigo_verificacion": "a1b2c3d4e5f60718",
        "emitida_en": datetime(2026, 1, 1, 14, 0, tzinfo=UTC),
    }
    datos.update(cambios)
    return Poliza(**datos)


def beneficiario(nombre="Mateo Gómez", documento="1098765432", porcentaje="60", **cambios):
    datos = {
        "nombre_completo": nombre,
        "tipo_documento": "CC",
        "numero_documento": documento,
        "parentesco": "Hijo",
        "porcentaje": Decimal(porcentaje),
    }
    datos.update(cambios)
    return Beneficiario(**datos)


def dos_beneficiarios() -> list[Beneficiario]:
    return [
        beneficiario(),
        beneficiario("Sofía Gómez", "1098765433", "40", parentesco="Hija"),
    ]


def solo_coberturas(**sumas: str) -> SolicitudModificacion:
    return SolicitudModificacion(
        coberturas_opcionales=[
            CoberturaSolicitada(codigo=codigo, suma_asegurada=Decimal(suma))
            for codigo, suma in sumas.items()
        ]
    )


def cotizacion(asesor_id: str | None = None) -> Cotizacion:
    return Cotizacion(
        cotizacion_id=COTIZACION,
        cliente_id=CLIENTE,
        ramo=RamoSeguro.VIDA,
        datos_riesgo={},
        estado=EstadoCotizacion.ACEPTADA,
        prima_total=Decimal("150000.00"),
        cobertura_principal=CoberturaPrincipal(
            codigo="FALLECIMIENTO",
            nombre="Cobertura por fallecimiento",
            suma_asegurada=Decimal("100000000.00"),
        ),
        asesor_id=asesor_id,
        creada_en=datetime(2025, 12, 31, 12, 0, tzinfo=UTC),
        vigente_hasta=datetime(2025, 12, 31, 12, 0, tzinfo=UTC) + timedelta(days=7),
    )


class Reloj:
    def __init__(self, ahora: datetime = AHORA):
        self.ahora = ahora

    def __call__(self) -> datetime:
        return self.ahora


@dataclass
class Entorno:
    servicio: ServicioEndosos
    polizas: RepositorioPolizasEnMemoria
    endosos: RepositorioEndososEnMemoria
    cotizaciones: RepositorioCotizacionesEnMemoria
    almacen: AlmacenEnMemoria
    reloj: Reloj


def crear_entorno(poliza_inicial: Poliza | None = None, asesor_id: str | None = None) -> Entorno:
    polizas = RepositorioPolizasEnMemoria()
    polizas.guardar(poliza_inicial or poliza())
    endosos = RepositorioEndososEnMemoria(polizas)
    cotizaciones = RepositorioCotizacionesEnMemoria()
    cotizaciones.guardar(cotizacion(asesor_id))
    almacen = AlmacenEnMemoria()
    reloj = Reloj()
    servicio = ServicioEndosos(polizas, endosos, cotizaciones, almacen, reloj=reloj)
    return Entorno(servicio, polizas, endosos, cotizaciones, almacen, reloj)
