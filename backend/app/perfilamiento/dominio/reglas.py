"""Reglas de scoring y suscripción (underwriting) del perfil de riesgo.

Funciones puras y deterministas: las mismas señales producen siempre el mismo resultado.
Cualquier cambio en pesos o umbrales debe subir `VERSION_REGLAS`.
"""

from dataclasses import dataclass

from app.perfilamiento.dominio.modelos import (
    ClasificacionRiesgo,
    Dictamen,
    NivelRiesgoZona,
    ReglaAplicada,
    SenalesPerfilamiento,
)

VERSION_REGLAS = "1.0.0"

# Scoring: pesos del riesgo financiero (Open Finance) y de entorno (Open Data).
PESO_FINANCIERO = 0.6
PESO_ENTORNO = 0.4
PESO_COMPORTAMIENTO_PAGO = 0.6
PESO_ENDEUDAMIENTO = 0.4
PESO_ESTABILIDAD = 0.7
PESO_ZONA = 0.3
RIESGO_POR_ZONA = {
    NivelRiesgoZona.BAJO: 0.1,
    NivelRiesgoZona.MEDIO: 0.5,
    NivelRiesgoZona.ALTO: 0.9,
}

# Clasificación del puntaje.
UMBRAL_RIESGO_MEDIO = 30
UMBRAL_RIESGO_ALTO = 70

# Suscripción.
UMBRAL_AJUSTE = 60
UMBRAL_RECHAZO = 85
ENDEUDAMIENTO_MAXIMO = 0.9
COMPORTAMIENTO_PAGO_MINIMO = 0.2
EXTRAPRIMA_BASE = 10.0
EXTRAPRIMA_POR_PUNTO = 1.0

# Factor para el motor de precios: 0.8 con puntaje 0 (descuento) hasta 1.5 con puntaje 100.
FACTOR_MINIMO = 0.8
FACTOR_RANGO = 0.7


@dataclass(frozen=True)
class ResultadoEvaluacion:
    puntaje_riesgo: int
    clasificacion: ClasificacionRiesgo
    dictamen: Dictamen
    factor_riesgo: float | None
    extraprima_porcentaje: float
    reglas_aplicadas: list[ReglaAplicada]


def calcular_puntaje(senales: SenalesPerfilamiento) -> int:
    """Puntaje de riesgo de 0 (mínimo) a 100 (máximo)."""
    finanzas = senales.open_finance
    entorno = senales.open_data

    riesgo_financiero = (
        PESO_COMPORTAMIENTO_PAGO * (1 - finanzas.comportamiento_pago)
        + PESO_ENDEUDAMIENTO * finanzas.nivel_endeudamiento
    )
    riesgo_entorno = (
        PESO_ESTABILIDAD * (1 - entorno.estabilidad)
        + PESO_ZONA * RIESGO_POR_ZONA[entorno.riesgo_zona]
    )
    puntaje = 100 * (PESO_FINANCIERO * riesgo_financiero + PESO_ENTORNO * riesgo_entorno)
    return int(round(puntaje))


def clasificar(puntaje: int) -> ClasificacionRiesgo:
    if puntaje < UMBRAL_RIESGO_MEDIO:
        return ClasificacionRiesgo.BAJO
    if puntaje < UMBRAL_RIESGO_ALTO:
        return ClasificacionRiesgo.MEDIO
    return ClasificacionRiesgo.ALTO


def calcular_factor_riesgo(puntaje: int) -> float:
    return round(FACTOR_MINIMO + (puntaje / 100) * FACTOR_RANGO, 4)


def evaluar(senales: SenalesPerfilamiento) -> ResultadoEvaluacion:
    """Aplica scoring y suscripción y deja la traza de las reglas usadas."""
    puntaje = calcular_puntaje(senales)
    clasificacion = clasificar(puntaje)
    reglas = [
        ReglaAplicada(
            codigo="SCORING",
            descripcion=(
                f"Puntaje = {PESO_FINANCIERO:.0%} riesgo financiero "
                f"+ {PESO_ENTORNO:.0%} riesgo de entorno."
            ),
            efecto=f"Puntaje {puntaje}, clasificación {clasificacion.value}.",
        )
    ]

    finanzas = senales.open_finance
    motivo_rechazo: ReglaAplicada | None = None
    if finanzas.nivel_endeudamiento >= ENDEUDAMIENTO_MAXIMO:
        motivo_rechazo = ReglaAplicada(
            codigo="RECHAZO_ENDEUDAMIENTO",
            descripcion=f"Endeudamiento igual o superior a {ENDEUDAMIENTO_MAXIMO:.0%}.",
            efecto="Dictamen RECHAZADO.",
        )
    elif finanzas.comportamiento_pago < COMPORTAMIENTO_PAGO_MINIMO:
        motivo_rechazo = ReglaAplicada(
            codigo="RECHAZO_COMPORTAMIENTO_PAGO",
            descripcion=f"Comportamiento de pago inferior a {COMPORTAMIENTO_PAGO_MINIMO:.0%}.",
            efecto="Dictamen RECHAZADO.",
        )
    elif puntaje >= UMBRAL_RECHAZO:
        motivo_rechazo = ReglaAplicada(
            codigo="RECHAZO_PUNTAJE",
            descripcion=f"Puntaje igual o superior a {UMBRAL_RECHAZO}.",
            efecto="Dictamen RECHAZADO.",
        )

    if motivo_rechazo is not None:
        reglas.append(motivo_rechazo)
        return ResultadoEvaluacion(
            puntaje_riesgo=puntaje,
            clasificacion=clasificacion,
            dictamen=Dictamen.RECHAZADO,
            factor_riesgo=None,
            extraprima_porcentaje=0.0,
            reglas_aplicadas=reglas,
        )

    factor = calcular_factor_riesgo(puntaje)
    if puntaje >= UMBRAL_AJUSTE:
        extraprima = EXTRAPRIMA_BASE + (puntaje - UMBRAL_AJUSTE) * EXTRAPRIMA_POR_PUNTO
        reglas.append(
            ReglaAplicada(
                codigo="AJUSTE_EXTRAPRIMA",
                descripcion=f"Puntaje entre {UMBRAL_AJUSTE} y {UMBRAL_RECHAZO - 1}.",
                efecto=f"Dictamen AJUSTADO con extraprima de {extraprima:.1f}%.",
            )
        )
        return ResultadoEvaluacion(
            puntaje_riesgo=puntaje,
            clasificacion=clasificacion,
            dictamen=Dictamen.AJUSTADO,
            factor_riesgo=factor,
            extraprima_porcentaje=extraprima,
            reglas_aplicadas=reglas,
        )

    reglas.append(
        ReglaAplicada(
            codigo="ACEPTACION_ESTANDAR",
            descripcion=f"Puntaje inferior a {UMBRAL_AJUSTE} y sin causales de rechazo.",
            efecto="Dictamen ACEPTADO con tarifa estándar.",
        )
    )
    return ResultadoEvaluacion(
        puntaje_riesgo=puntaje,
        clasificacion=clasificacion,
        dictamen=Dictamen.ACEPTADO,
        factor_riesgo=factor,
        extraprima_porcentaje=0.0,
        reglas_aplicadas=reglas,
    )
