import logging

import pytest

from app.perfilamiento.dominio.modelos import OrigenSenales, SenalesOpenFinance
from app.perfilamiento.enriquecimiento.modelos import OrigenDato, TipoFuente
from app.perfilamiento.enriquecimiento.servicio import (
    EnriquecimientoNoDisponible,
    ServicioEnriquecimiento,
    SinConsentimientoVigente,
)
from tests.enriquecimiento.dobles import ENTORNO, FINANZAS, Escenario, FuenteDoble

AUDITORIA = "solventa.auditoria.enriquecimiento"


def test_consolida_ambas_fuentes_en_el_modelo_unificado():
    escenario = Escenario().con_consentimiento()

    resultado = escenario.enriquecer()

    assert resultado.senales.open_finance == FINANZAS
    assert resultado.senales.open_data == ENTORNO
    assert resultado.senales.consentimiento_id == "CONS-001"
    assert resultado.senales.origen is OrigenSenales.FUENTES_EXTERNAS
    assert resultado.cotizacion_id == "COT-001"
    assert [t.origen for t in resultado.fuentes] == [OrigenDato.FUENTE_EXTERNA] * 2
    assert {t.tipo for t in resultado.fuentes} == {TipoFuente.OPEN_FINANCE, TipoFuente.OPEN_DATA}


def test_sin_consentimiento_no_se_consulta_ninguna_fuente():
    escenario = Escenario()

    with pytest.raises(SinConsentimientoVigente):
        escenario.enriquecer()

    assert escenario.open_finance.consultas == 0
    assert escenario.open_data.consultas == 0


def test_consentimiento_vencido_no_permite_consultar():
    escenario = Escenario().con_consentimiento(dias=1)
    escenario.reloj.avanzar(days=1)

    with pytest.raises(SinConsentimientoVigente):
        escenario.enriquecer()

    assert escenario.open_finance.consultas == 0


def test_el_consentimiento_de_otro_cliente_no_sirve():
    escenario = Escenario().con_consentimiento(cliente_id="CLI-002")

    with pytest.raises(SinConsentimientoVigente):
        escenario.enriquecer("CLI-001")


def test_si_falla_open_finance_usa_su_dato_en_cache_y_lo_registra(caplog):
    escenario = Escenario().con_consentimiento()
    escenario.enriquecer()
    escenario.open_finance.falla = "respuesta HTTP 503"
    escenario.reloj.avanzar(hours=1)

    with caplog.at_level(logging.WARNING, logger=AUDITORIA):
        resultado = escenario.enriquecer()

    assert resultado.senales.origen is OrigenSenales.CACHE
    assert resultado.senales.open_finance == FINANZAS
    trazas = {t.tipo: t for t in resultado.fuentes}
    assert trazas[TipoFuente.OPEN_FINANCE].origen is OrigenDato.CACHE
    assert trazas[TipoFuente.OPEN_FINANCE].motivo_cache == "respuesta HTTP 503"
    assert trazas[TipoFuente.OPEN_DATA].origen is OrigenDato.FUENTE_EXTERNA
    assert "uso_de_cache cliente=CLI-001 fuente=OPEN_FINANCE" in caplog.text


def test_si_falla_open_data_usa_su_dato_en_cache():
    escenario = Escenario().con_consentimiento()
    escenario.enriquecer()
    escenario.open_data.falla = "error de conexión"

    resultado = escenario.enriquecer()

    trazas = {t.tipo: t for t in resultado.fuentes}
    assert trazas[TipoFuente.OPEN_DATA].origen is OrigenDato.CACHE
    assert trazas[TipoFuente.OPEN_FINANCE].origen is OrigenDato.FUENTE_EXTERNA
    assert resultado.senales.open_data == ENTORNO


def test_una_fuente_lenta_se_corta_en_el_tiempo_limite_y_usa_cache():
    escenario = Escenario(tiempo_limite=0.05).con_consentimiento()
    escenario.enriquecer()
    escenario.open_finance.demora = 1.0

    resultado = escenario.enriquecer()

    traza = next(t for t in resultado.fuentes if t.tipo is TipoFuente.OPEN_FINANCE)
    assert traza.origen is OrigenDato.CACHE
    assert traza.motivo_cache == "tiempo de espera agotado"


def test_falla_sin_cache_no_inventa_datos(caplog):
    escenario = Escenario().con_consentimiento()
    escenario.open_data.falla = "respuesta HTTP 500"

    with caplog.at_level(logging.WARNING, logger=AUDITORIA):
        with pytest.raises(EnriquecimientoNoDisponible) as error:
            escenario.enriquecer()

    assert error.value.tipo is TipoFuente.OPEN_DATA
    assert "fuente_no_disponible_sin_cache" in caplog.text
    assert escenario.servicio.ultimo("CLI-001") is None


def test_el_dato_en_cache_vencido_no_se_usa():
    escenario = Escenario().con_consentimiento()
    escenario.enriquecer()
    escenario.open_finance.falla = "respuesta HTTP 503"
    escenario.reloj.avanzar(hours=24)

    with pytest.raises(EnriquecimientoNoDisponible):
        escenario.enriquecer()


def test_la_cache_no_se_comparte_entre_clientes():
    escenario = Escenario().con_consentimiento("CLI-001").con_consentimiento("CLI-002")
    escenario.enriquecer("CLI-001")
    escenario.open_finance.falla = "respuesta HTTP 503"

    with pytest.raises(EnriquecimientoNoDisponible):
        escenario.enriquecer("CLI-002")


def test_cuando_la_fuente_se_recupera_se_vuelve_a_usar_y_se_refresca_la_cache():
    escenario = Escenario().con_consentimiento()
    escenario.enriquecer()
    escenario.open_finance.falla = "respuesta HTTP 503"
    escenario.enriquecer()

    escenario.open_finance.falla = None
    escenario.open_finance.senales = SenalesOpenFinance(
        comportamiento_pago=0.5, nivel_endeudamiento=0.6
    )
    resultado = escenario.enriquecer()

    assert resultado.senales.origen is OrigenSenales.FUENTES_EXTERNAS
    assert resultado.senales.open_finance.comportamiento_pago == 0.5


def test_las_fuentes_se_consultan_en_paralelo():
    escenario = Escenario(tiempo_limite=0.5).con_consentimiento()
    escenario.open_finance.demora = 0.15
    escenario.open_data.demora = 0.15

    resultado = escenario.enriquecer()

    latencias = [t.latencia_ms for t in resultado.fuentes]
    assert all(150 <= latencia < 290 for latencia in latencias)


def test_el_ultimo_resultado_queda_consultable():
    escenario = Escenario().con_consentimiento()

    resultado = escenario.enriquecer()

    assert escenario.servicio.ultimo("CLI-001") == resultado


def test_nueva_fuente_se_incorpora_sin_cambiar_el_servicio_ni_el_contrato():
    """EC14: un segundo agregador de Open Finance entra como otro adaptador del mismo puerto."""
    base = Escenario().con_consentimiento()
    otro_agregador = FuenteDoble(
        TipoFuente.OPEN_FINANCE,
        SenalesOpenFinance(comportamiento_pago=0.7, nivel_endeudamiento=0.4),
        proveedor="agregador-b",
    )
    servicio = ServicioEnriquecimiento(
        fuentes=[otro_agregador, base.open_data],
        cache=base.cache,
        consentimientos=base.consentimientos,
        tiempo_limite=0.2,
        reloj=base.reloj,
    )
    base.servicio = servicio

    resultado = base.enriquecer()

    assert set(resultado.senales.model_dump()) == set(
        Escenario().con_consentimiento().enriquecer().senales.model_dump()
    )
    assert resultado.senales.open_finance.comportamiento_pago == 0.7
    assert resultado.fuentes[0].proveedor == "agregador-b"


def test_el_servicio_exige_una_fuente_de_cada_tipo():
    base = Escenario()

    with pytest.raises(ValueError, match="OPEN_DATA"):
        ServicioEnriquecimiento(
            fuentes=[base.open_finance],
            cache=base.cache,
            consentimientos=base.consentimientos,
            tiempo_limite=0.2,
        )
