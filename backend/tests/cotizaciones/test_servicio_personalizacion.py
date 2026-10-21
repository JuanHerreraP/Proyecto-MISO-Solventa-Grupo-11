from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.cotizaciones.dominio.modelos import CoberturaPrincipal
from app.cotizaciones.dominio.rating import ResultadoTarifaBase
from app.cotizaciones.servicio_personalizacion import (
    RiesgoNoAsegurableError,
    ServicioPersonalizacionCotizacion,
)
from app.perfilamiento.dominio.modelos import (
    ClasificacionRiesgo,
    Dictamen,
    OrigenSenales,
    PerfilRiesgo,
)
from app.perfilamiento.enriquecimiento.memoria import RepositorioConsentimientosEnMemoria
from app.perfilamiento.enriquecimiento.modelos import Consentimiento
from app.perfilamiento.repositorio import RepositorioPerfilesEnMemoria

AHORA = datetime(2027, 1, 10, tzinfo=timezone.utc)


def tarifa_base(prima: str = "100000.00") -> ResultadoTarifaBase:
    return ResultadoTarifaBase(
        prima_total=Decimal(prima),
        cobertura_principal=CoberturaPrincipal(
            codigo="FALLECIMIENTO",
            nombre="Cobertura por fallecimiento",
            suma_asegurada=Decimal("100000000.00"),
        ),
    )


def perfil(
    *,
    dictamen: Dictamen = Dictamen.AJUSTADO,
    factor_riesgo: float | None = 1.2,
    consentimiento_id: str = "CONS-001",
) -> PerfilRiesgo:
    return PerfilRiesgo(
        perfil_id="PERFIL-001",
        cliente_id="CLI-001",
        consentimiento_id=consentimiento_id,
        puntaje_riesgo=55,
        clasificacion=ClasificacionRiesgo.MEDIO,
        dictamen=dictamen,
        factor_riesgo=factor_riesgo,
        extraprima_porcentaje=20,
        origen_senales=OrigenSenales.FUENTES_EXTERNAS,
        version_reglas="1.0.0",
        reglas_aplicadas=[],
        fecha_calculo=AHORA,
        tiempo_calculo_ms=10,
    )


def servicio(
    perfil_riesgo: PerfilRiesgo | None = None,
    *,
    consentimiento_vigente: bool = True,
    consentimiento_id: str = "CONS-001",
) -> ServicioPersonalizacionCotizacion:
    perfiles = RepositorioPerfilesEnMemoria()
    if perfil_riesgo is not None:
        perfiles.guardar(perfil_riesgo)

    consentimientos = RepositorioConsentimientosEnMemoria()
    vencimiento = AHORA + timedelta(hours=1)
    if not consentimiento_vigente:
        vencimiento = AHORA - timedelta(seconds=1)
    consentimientos.registrar(
        Consentimiento(
            consentimiento_id=consentimiento_id,
            cliente_id="CLI-001",
            vence_en=vencimiento,
        )
    )

    return ServicioPersonalizacionCotizacion(
        perfiles,
        consentimientos,
        reloj=lambda: AHORA,
    )


def test_personaliza_la_prima_con_perfil_y_consentimiento_vigentes() -> None:
    resultado = servicio(perfil()).personalizar("CLI-001", tarifa_base())

    assert resultado.prima_base == Decimal("100000.00")
    assert resultado.prima_total == Decimal("120000.00")
    assert resultado.personalizada is True
    assert resultado.factor_riesgo == Decimal("1.2")
    assert resultado.perfil_riesgo_id == "PERFIL-001"
    assert resultado.consentimiento_id == "CONS-001"
    assert resultado.version_reglas == "1.0.0"


@pytest.mark.parametrize(
    "servicio_sin_contexto",
    [
        servicio(),
        servicio(perfil(), consentimiento_vigente=False),
        servicio(perfil(), consentimiento_id="CONS-OTRO"),
    ],
)
def test_conserva_la_tarifa_base_sin_perfil_autorizado(
    servicio_sin_contexto: ServicioPersonalizacionCotizacion,
) -> None:
    resultado = servicio_sin_contexto.personalizar("CLI-001", tarifa_base())

    assert resultado.prima_total == Decimal("100000.00")
    assert resultado.personalizada is False
    assert resultado.factor_riesgo == Decimal("1")
    assert resultado.perfil_riesgo_id is None


def test_rechaza_la_cotizacion_cuando_el_dictamen_no_es_asegurable() -> None:
    perfil_rechazado = perfil(dictamen=Dictamen.RECHAZADO, factor_riesgo=None)

    with pytest.raises(RiesgoNoAsegurableError):
        servicio(perfil_rechazado).personalizar("CLI-001", tarifa_base())


def test_mantiene_la_prima_minima_despues_de_personalizar() -> None:
    perfil_bajo = perfil(dictamen=Dictamen.ACEPTADO, factor_riesgo=0.8)

    resultado = servicio(perfil_bajo).personalizar("CLI-001", tarifa_base("5000.00"))

    assert resultado.prima_total == Decimal("5000.00")
