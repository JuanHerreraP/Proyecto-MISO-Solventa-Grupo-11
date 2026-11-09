"""Fábricas en memoria para probar el historial de la póliza (HU25)."""

from datetime import UTC, date, datetime
from decimal import Decimal

from app.desembolsos.modelos import Desembolso, EstadoDesembolso, MedioDesembolso
from app.pagos.modelos import EstadoPago, MetodoPago, Pago
from app.polizas.dominio.endosos import CambioEndoso, Endoso, TipoCambio, TipoEndoso
from app.polizas.dominio.modelos import (
    CoberturaPoliza,
    EstadoRegistroPoliza,
    Poliza,
    RamoPoliza,
)

CLIENTE = "CLI-001"
COTIZACION = "COT-001"
POLIZA = "POL-001"

HUELLA = "a" * 64


def poliza(**cambios) -> Poliza:
    datos = {
        "poliza_id": POLIZA,
        "numero_poliza": "SOLV-VIA-2026-00152",
        "cliente_id": CLIENTE,
        "cotizacion_id": COTIZACION,
        "ramo": RamoPoliza.VIAJE,
        "titular_nombre": "Ana Pérez",
        "titular_tipo_documento": "CC",
        "titular_numero_documento": "1012345678",
        "fecha_inicio": date(2026, 10, 20),
        "fecha_fin": date(2026, 12, 31),
        "prima_total": Decimal("125000.00"),
        "cobertura_principal": CoberturaPoliza(
            codigo="ASISTENCIA_MEDICA",
            nombre="Asistencia médica en viaje",
            suma_asegurada=Decimal("40000000.00"),
        ),
        "codigo_verificacion": "a1b2c3d4e5f60718",
        "emitida_en": datetime(2026, 10, 20, 14, 5, tzinfo=UTC),
    }
    datos.update(cambios)
    if datos.get("estado") is EstadoRegistroPoliza.CANCELADA and "cancelada_en" not in cambios:
        datos["cancelada_en"] = datetime(2026, 11, 6, 10, 20, tzinfo=UTC)
    return Poliza(**datos)


def pago(**cambios) -> Pago:
    datos = {
        "pago_id": "PAY-001",
        "cotizacion_id": COTIZACION,
        "cliente_id": CLIENTE,
        "idempotency_key": "llave-001",
        "huella_solicitud": HUELLA,
        "metodo": MetodoPago.TARJETA,
        "monto": Decimal("125000.00"),
        "moneda": "COP",
        "estado": EstadoPago.APROBADO,
        "referencia_pasarela": "PSP-88910",
        "creado_en": datetime(2026, 10, 20, 13, 45, tzinfo=UTC),
        "actualizado_en": datetime(2026, 10, 20, 13, 46, tzinfo=UTC),
    }
    datos.update(cambios)
    return Pago(**datos)


def endoso(**cambios) -> Endoso:
    datos = {
        "endoso_id": "END-001-002",
        "poliza_id": POLIZA,
        "numero_endoso": 2,
        "tipo": TipoEndoso.COBERTURAS,
        "solicitado_por": "USR-1",
        "rol_solicitante": "CLIENTE",
        "huella_solicitud": HUELLA,
        "ip_solicitante": "10.0.0.1",
        "user_agent": "pruebas",
        "fecha_efecto": date(2026, 11, 4),
        "dias_vigencia": 73,
        "dias_restantes": 58,
        "prima_anterior": Decimal("125000.00"),
        "ajuste_prima": Decimal("25000.00"),
        "prima_nueva": Decimal("150000.00"),
        "moneda": "COP",
        "cambios": [
            CambioEndoso(
                tipo=TipoCambio.COBERTURA_INCLUIDA,
                descripcion="Se incluye Pérdida de equipaje.",
                despues={
                    "codigo": "EQUIPAJE",
                    "nombre": "Pérdida de equipaje",
                    "suma_asegurada": "5000000.00",
                },
            )
        ],
        "coberturas_opcionales": [],
        "beneficiarios": [],
        "clave_documento": "polizas/POL-001/endosos/END-001-002.pdf",
        "huella_documento": "b" * 64,
        "tamano_documento": 1024,
        "creado_en": datetime(2026, 11, 4, 15, 40, tzinfo=UTC),
    }
    datos.update(cambios)
    return Endoso(**datos)


def desembolso(**cambios) -> Desembolso:
    datos = {
        "desembolso_id": "DES-001",
        "siniestro_id": "SIN-001",
        "poliza_id": POLIZA,
        "cliente_id": CLIENTE,
        "monto": Decimal("850000.00"),
        "moneda": "COP",
        "medio": MedioDesembolso.CUENTA_BANCARIA,
        "estado": EstadoDesembolso.COMPLETADA,
        "referencia_transaccion": "TRF-889900",
        "creado_en": datetime(2026, 11, 7, 14, 30, tzinfo=UTC),
        "actualizado_en": datetime(2026, 11, 7, 14, 31, tzinfo=UTC),
        "completado_en": datetime(2026, 11, 7, 14, 31, tzinfo=UTC),
    }
    datos.update(cambios)
    return Desembolso(**datos)
