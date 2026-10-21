"""Cálculo base de prima y cobertura principal por ramo (HU03 / BPM-154)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import cast

from app.cotizaciones.dominio.modelos import CoberturaPrincipal, RamoSeguro
from app.cotizaciones.dominio.validacion import validar_datos_riesgo

VERSION_TARIFAS = "1.0.0"
PRIMA_MINIMA = Decimal("5000.00")
PRECISION_MONEDA = Decimal("0.01")

TARIFA_DIARIA_VIAJE = Decimal("0.00015")
TARIFA_MENSUAL_DISPOSITIVO = Decimal("0.007")
TARIFA_MENSUAL_VIDA = Decimal("0.00035")
FACTOR_FUMADOR = Decimal("1.35")
TARIFA_PARAMETRICO_VUELO = Decimal("0.05")
TARIFA_PARAMETRICO_CLIMA = Decimal("0.08")


@dataclass(frozen=True)
class ResultadoTarifaBase:
    """Resultado reproducible del motor de rating antes de personalizar por riesgo."""

    prima_total: Decimal
    cobertura_principal: CoberturaPrincipal
    version_tarifas: str = VERSION_TARIFAS


def calcular_prima_y_cobertura(
    ramo: RamoSeguro,
    datos_riesgo: dict[str, object],
) -> ResultadoTarifaBase:
    """Valida la entrada y ejecuta el calculador registrado para el ramo."""

    datos_normalizados = validar_datos_riesgo(ramo, datos_riesgo)
    return CALCULADORES_POR_RAMO[ramo](datos_normalizados)


def _calcular_viaje(datos: dict[str, object]) -> ResultadoTarifaBase:
    inicio = cast(date, datos["fecha_inicio"])
    fin = cast(date, datos["fecha_fin"])
    viajeros = cast(int, datos["numero_viajeros"])
    valor_asegurado = cast(Decimal, datos["valor_asegurado"])
    dias = (fin - inicio).days

    prima = valor_asegurado * TARIFA_DIARIA_VIAJE * dias * viajeros
    return ResultadoTarifaBase(
        prima_total=_normalizar_prima(prima),
        cobertura_principal=CoberturaPrincipal(
            codigo="ASISTENCIA_VIAJE",
            nombre="Asistencia integral de viaje",
            suma_asegurada=valor_asegurado,
            descripcion="Atención de emergencias cubiertas durante el viaje contratado.",
        ),
    )


def _calcular_dispositivo(datos: dict[str, object]) -> ResultadoTarifaBase:
    valor_dispositivo = cast(Decimal, datos["valor_dispositivo"])
    meses = cast(int, datos["meses_cobertura"])

    prima = valor_dispositivo * TARIFA_MENSUAL_DISPOSITIVO * meses
    return ResultadoTarifaBase(
        prima_total=_normalizar_prima(prima),
        cobertura_principal=CoberturaPrincipal(
            codigo="DANO_ROBO_DISPOSITIVO",
            nombre="Daño accidental y robo",
            suma_asegurada=valor_dispositivo,
            descripcion="Protección del dispositivo hasta su valor comercial declarado.",
        ),
    )


def _calcular_vida(datos: dict[str, object]) -> ResultadoTarifaBase:
    valor_asegurado = cast(Decimal, datos["valor_asegurado"])
    meses = cast(int, datos["meses_cobertura"])
    fumador = cast(bool, datos["fumador"])
    factor_habito = FACTOR_FUMADOR if fumador else Decimal("1")

    prima = valor_asegurado * TARIFA_MENSUAL_VIDA * meses * factor_habito
    return ResultadoTarifaBase(
        prima_total=_normalizar_prima(prima),
        cobertura_principal=CoberturaPrincipal(
            codigo="FALLECIMIENTO",
            nombre="Cobertura por fallecimiento",
            suma_asegurada=valor_asegurado,
            descripcion="Pago del valor asegurado a los beneficiarios de la póliza.",
        ),
    )


def _calcular_parametrico(datos: dict[str, object]) -> ResultadoTarifaBase:
    valor_asegurado = cast(Decimal, datos["valor_asegurado"])
    tipo_evento = cast(str, datos["tipo_evento"])
    tarifa, codigo, nombre, descripcion = TARIFAS_PARAMETRICAS[tipo_evento]

    prima = valor_asegurado * tarifa
    return ResultadoTarifaBase(
        prima_total=_normalizar_prima(prima),
        cobertura_principal=CoberturaPrincipal(
            codigo=codigo,
            nombre=nombre,
            suma_asegurada=valor_asegurado,
            descripcion=descripcion,
        ),
    )


def _normalizar_prima(prima: Decimal) -> Decimal:
    """Aplica la prima mínima y redondea de manera determinista a centavos."""

    return max(prima, PRIMA_MINIMA).quantize(PRECISION_MONEDA, rounding=ROUND_HALF_UP)


TARIFAS_PARAMETRICAS: dict[str, tuple[Decimal, str, str, str]] = {
    "RETRASO_VUELO": (
        TARIFA_PARAMETRICO_VUELO,
        "COMPENSACION_RETRASO_VUELO",
        "Compensación por retraso de vuelo",
        "Pago automático cuando el retraso supera el umbral contratado.",
    ),
    "EVENTO_CLIMATICO": (
        TARIFA_PARAMETRICO_CLIMA,
        "COMPENSACION_EVENTO_CLIMATICO",
        "Compensación por evento climático",
        "Pago automático cuando el indicador climático supera el umbral contratado.",
    ),
}

CalculadorRamo = Callable[[dict[str, object]], ResultadoTarifaBase]

CALCULADORES_POR_RAMO: dict[RamoSeguro, CalculadorRamo] = {
    RamoSeguro.VIAJE: _calcular_viaje,
    RamoSeguro.PROTECCION_DISPOSITIVOS: _calcular_dispositivo,
    RamoSeguro.VIDA: _calcular_vida,
    RamoSeguro.PARAMETRICO: _calcular_parametrico,
}
