import pytest

from app.perfilamiento.dominio import reglas
from app.perfilamiento.dominio.modelos import ClasificacionRiesgo, Dictamen
from tests.perfilamiento.fabrica import senales


def test_perfil_de_bajo_riesgo_se_acepta_con_tarifa_estandar():
    resultado = reglas.evaluar(senales())

    assert resultado.puntaje_riesgo == 12
    assert resultado.clasificacion is ClasificacionRiesgo.BAJO
    assert resultado.dictamen is Dictamen.ACEPTADO
    assert resultado.extraprima_porcentaje == 0
    assert resultado.factor_riesgo == pytest.approx(0.884)


def test_perfil_de_riesgo_intermedio_se_ajusta_con_extraprima():
    resultado = reglas.evaluar(
        senales(
            comportamiento_pago=0.4,
            nivel_endeudamiento=0.7,
            estabilidad=0.3,
            riesgo_zona="ALTO",
        )
    )

    assert resultado.puntaje_riesgo == 69
    assert resultado.clasificacion is ClasificacionRiesgo.MEDIO
    assert resultado.dictamen is Dictamen.AJUSTADO
    assert resultado.extraprima_porcentaje == pytest.approx(19.0)
    assert resultado.factor_riesgo == pytest.approx(1.283)


def test_perfil_de_alto_riesgo_se_rechaza_por_puntaje():
    resultado = reglas.evaluar(
        senales(
            comportamiento_pago=0.2,
            nivel_endeudamiento=0.85,
            estabilidad=0.0,
            riesgo_zona="ALTO",
        )
    )

    assert resultado.puntaje_riesgo >= reglas.UMBRAL_RECHAZO
    assert resultado.clasificacion is ClasificacionRiesgo.ALTO
    assert resultado.dictamen is Dictamen.RECHAZADO
    assert resultado.factor_riesgo is None
    assert resultado.reglas_aplicadas[-1].codigo == "RECHAZO_PUNTAJE"


def test_endeudamiento_excesivo_rechaza_aunque_el_puntaje_sea_moderado():
    resultado = reglas.evaluar(senales(nivel_endeudamiento=0.9))

    assert resultado.puntaje_riesgo < reglas.UMBRAL_AJUSTE
    assert resultado.dictamen is Dictamen.RECHAZADO
    assert resultado.reglas_aplicadas[-1].codigo == "RECHAZO_ENDEUDAMIENTO"


def test_mal_comportamiento_de_pago_rechaza():
    resultado = reglas.evaluar(senales(comportamiento_pago=0.19))

    assert resultado.dictamen is Dictamen.RECHAZADO
    assert resultado.reglas_aplicadas[-1].codigo == "RECHAZO_COMPORTAMIENTO_PAGO"


@pytest.mark.parametrize(
    ("puntaje", "esperada"),
    [
        (0, ClasificacionRiesgo.BAJO),
        (29, ClasificacionRiesgo.BAJO),
        (30, ClasificacionRiesgo.MEDIO),
        (69, ClasificacionRiesgo.MEDIO),
        (70, ClasificacionRiesgo.ALTO),
        (100, ClasificacionRiesgo.ALTO),
    ],
)
def test_limites_de_clasificacion(puntaje, esperada):
    assert reglas.clasificar(puntaje) is esperada


def test_puntaje_en_los_extremos():
    mejor = senales(comportamiento_pago=1, nivel_endeudamiento=0, estabilidad=1)
    peor = senales(comportamiento_pago=0, nivel_endeudamiento=1, estabilidad=0, riesgo_zona="ALTO")

    assert reglas.calcular_puntaje(mejor) == 1
    assert reglas.calcular_puntaje(peor) == 99


def test_extraprima_en_los_limites_del_rango_de_ajuste():
    en_el_umbral = reglas.evaluar(
        senales(
            comportamiento_pago=0.5,
            nivel_endeudamiento=0.5,
            estabilidad=0.3,
            riesgo_zona="ALTO",
        )
    )
    justo_antes_del_rechazo = reglas.evaluar(
        senales(
            comportamiento_pago=0.2,
            nivel_endeudamiento=0.685,
            estabilidad=0.0,
            riesgo_zona="ALTO",
        )
    )

    assert en_el_umbral.puntaje_riesgo == reglas.UMBRAL_AJUSTE
    assert en_el_umbral.dictamen is Dictamen.AJUSTADO
    assert en_el_umbral.extraprima_porcentaje == pytest.approx(10.0)

    assert justo_antes_del_rechazo.puntaje_riesgo == reglas.UMBRAL_RECHAZO - 1
    assert justo_antes_del_rechazo.dictamen is Dictamen.AJUSTADO
    assert justo_antes_del_rechazo.extraprima_porcentaje == pytest.approx(34.0)


def test_las_mismas_senales_producen_el_mismo_resultado():
    entrada = senales(comportamiento_pago=0.55, nivel_endeudamiento=0.45, riesgo_zona="MEDIO")

    assert reglas.evaluar(entrada) == reglas.evaluar(entrada)


def test_el_factor_de_riesgo_cubre_el_rango_del_motor_de_precios():
    assert reglas.calcular_factor_riesgo(0) == pytest.approx(0.8)
    assert reglas.calcular_factor_riesgo(100) == pytest.approx(1.5)
