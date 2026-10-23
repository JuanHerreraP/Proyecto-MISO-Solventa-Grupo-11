"""Pólizas de prueba para la billetera (HU07)."""

from datetime import UTC, date, datetime
from decimal import Decimal

from app.polizas.dominio.modelos import (
    CoberturaPoliza,
    EstadoRegistroPoliza,
    Poliza,
    RamoPoliza,
)

# 2026-10-21 10:00 en Bogotá.
AHORA = datetime(2026, 10, 21, 15, 0, tzinfo=UTC)
HOY = date(2026, 10, 21)


def poliza(**cambios) -> Poliza:
    datos = {
        "poliza_id": "POL-1",
        "numero_poliza": "SOL-VI-000001",
        "cliente_id": "CLI-001",
        "ramo": RamoPoliza.VIAJE,
        "titular_nombre": "Ana Pérez",
        "titular_tipo_documento": "CC",
        "titular_numero_documento": "1012345678",
        "fecha_inicio": date(2026, 10, 1),
        "fecha_fin": date(2026, 12, 31),
        "prima_total": Decimal("85000.00"),
        "cobertura_principal": CoberturaPoliza(
            codigo="ASISTENCIA_MEDICA",
            nombre="Asistencia médica en viaje",
            suma_asegurada=Decimal("40000000.00"),
        ),
        "codigo_verificacion": "a1b2c3d4e5f60718",
        "emitida_en": datetime(2026, 9, 30, 14, 0, tzinfo=UTC),
    }
    datos.update(cambios)
    if datos.get("estado") is EstadoRegistroPoliza.CANCELADA and "cancelada_en" not in cambios:
        datos["cancelada_en"] = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
    return Poliza(**datos)
