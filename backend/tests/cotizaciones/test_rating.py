from decimal import Decimal

import pytest

from app.cotizaciones.dominio.modelos import RamoSeguro
from app.cotizaciones.dominio.rating import VERSION_TARIFAS, calcular_prima_y_cobertura
from app.cotizaciones.dominio.validacion import DatosRiesgoInvalidosError


@pytest.mark.parametrize(
    ("ramo", "datos", "prima_esperada", "codigo_cobertura"),
    [
        (
            RamoSeguro.VIAJE,
            {
                "destino": "Lima",
                "fecha_inicio": "2027-01-10",
                "fecha_fin": "2027-01-20",
                "numero_viajeros": 2,
                "valor_asegurado": 15_000_000,
            },
            Decimal("45000.00"),
            "ASISTENCIA_VIAJE",
        ),
        (
            RamoSeguro.PROTECCION_DISPOSITIVOS,
            {
                "tipo_dispositivo": "CELULAR",
                "marca": "Acme",
                "modelo": "X1",
                "valor_dispositivo": 3_500_000,
                "fecha_compra": "2026-01-10",
                "meses_cobertura": 12,
            },
            Decimal("294000.00"),
            "DANO_ROBO_DISPOSITIVO",
        ),
        (
            RamoSeguro.VIDA,
            {
                "fecha_nacimiento": "1990-05-20",
                "valor_asegurado": 100_000_000,
                "meses_cobertura": 12,
                "fumador": False,
            },
            Decimal("420000.00"),
            "FALLECIMIENTO",
        ),
        (
            RamoSeguro.PARAMETRICO,
            {
                "tipo_evento": "RETRASO_VUELO",
                "fecha_inicio": "2027-02-01",
                "fecha_fin": "2027-02-02",
                "umbral_disparo": 180,
                "valor_asegurado": 1_000_000,
                "numero_vuelo": "AV123",
            },
            Decimal("50000.00"),
            "COMPENSACION_RETRASO_VUELO",
        ),
    ],
)
def test_calcula_prima_y_cobertura_principal_por_ramo(
    ramo: RamoSeguro,
    datos: dict[str, object],
    prima_esperada: Decimal,
    codigo_cobertura: str,
) -> None:
    resultado = calcular_prima_y_cobertura(ramo, datos)

    assert resultado.prima_total == prima_esperada
    assert resultado.cobertura_principal.codigo == codigo_cobertura
    assert resultado.version_tarifas == VERSION_TARIFAS


def test_aplica_factor_adicional_al_fumador() -> None:
    datos = {
        "fecha_nacimiento": "1990-05-20",
        "valor_asegurado": 100_000_000,
        "meses_cobertura": 12,
        "fumador": True,
    }

    resultado = calcular_prima_y_cobertura(RamoSeguro.VIDA, datos)

    assert resultado.prima_total == Decimal("567000.00")


def test_diferencia_la_cobertura_parametrica_climatica() -> None:
    datos = {
        "tipo_evento": "EVENTO_CLIMATICO",
        "fecha_inicio": "2027-02-01",
        "fecha_fin": "2027-02-02",
        "umbral_disparo": 50,
        "valor_asegurado": 1_000_000,
        "ubicacion": "Cartagena",
    }

    resultado = calcular_prima_y_cobertura(RamoSeguro.PARAMETRICO, datos)

    assert resultado.prima_total == Decimal("80000.00")
    assert resultado.cobertura_principal.codigo == "COMPENSACION_EVENTO_CLIMATICO"


def test_aplica_prima_minima() -> None:
    datos = {
        "destino": "Lima",
        "fecha_inicio": "2027-01-10",
        "fecha_fin": "2027-01-11",
        "numero_viajeros": 1,
        "valor_asegurado": 100_000,
    }

    resultado = calcular_prima_y_cobertura(RamoSeguro.VIAJE, datos)

    assert resultado.prima_total == Decimal("5000.00")


def test_no_calcula_si_los_datos_del_riesgo_son_invalidos() -> None:
    with pytest.raises(DatosRiesgoInvalidosError):
        calcular_prima_y_cobertura(RamoSeguro.VIAJE, {"destino": "Lima"})
