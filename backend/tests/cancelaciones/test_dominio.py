"""Reglas de la cancelación: saldo a favor por días y motivos de bloqueo (HU22)."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.polizas.dominio.cancelacion import (
    CodigoBloqueo,
    MotivoCancelacion,
    PeriodoPagado,
    SolicitudCancelacion,
    calcular_saldo,
    proponer_cancelacion,
)
from app.polizas.dominio.modelos import EstadoRegistroPoliza
from tests.endosos.fabrica import HOY, poliza

# La póliza de la fábrica es de vida, del 1 de enero al 31 de diciembre de 2026 (365 días) con
# prima de 150.000. Hoy (2 de julio) le quedan 182 días después de hoy.


def test_saldo_proporcional_a_los_dias_sin_usar() -> None:
    propuesta = proponer_cancelacion(poliza(), HOY)

    assert propuesta.cancelable is True
    assert propuesta.bloqueos == ()
    assert propuesta.dias_totales == 365
    assert propuesta.dias_no_transcurridos == 182
    assert propuesta.saldo_estimado == Decimal("74794.52")  # 150000 x 182 / 365
    assert propuesta.fecha_efecto == HOY
    assert propuesta.prima_total == Decimal("150000.00")


def test_el_dia_de_hoy_cuenta_como_usado() -> None:
    ultimo_dia = proponer_cancelacion(poliza(), date(2026, 12, 31))
    primer_dia = proponer_cancelacion(poliza(), date(2026, 1, 1))

    assert ultimo_dia.dias_no_transcurridos == 0
    assert ultimo_dia.saldo_estimado == Decimal("0.00")
    assert primer_dia.dias_no_transcurridos == 364
    assert primer_dia.saldo_estimado == Decimal("149589.04")  # 150000 x 364 / 365


def test_una_poliza_que_aun_no_empieza_se_devuelve_completa() -> None:
    propuesta = proponer_cancelacion(poliza(), date(2025, 12, 1))

    assert propuesta.dias_no_transcurridos == 365
    assert propuesta.saldo_estimado == Decimal("150000.00")


def test_una_poliza_renovada_con_anticipacion_suma_el_saldo_de_los_dos_periodos() -> None:
    actual = PeriodoPagado(date(2026, 1, 1), date(2026, 12, 31), Decimal("150000.00"))
    siguiente = PeriodoPagado(date(2027, 1, 1), date(2027, 12, 31), Decimal("160000.00"))

    saldo, totales, sin_usar = calcular_saldo([actual, siguiente], date(2026, 12, 2))

    # Periodo actual: 150000 x 29 / 365 = 11917,81. El siguiente no empezó: 160000 completo.
    assert saldo == Decimal("171917.81")
    assert totales == 730
    assert sin_usar == 29 + 365


@pytest.mark.parametrize(
    ("prima", "esperado"),
    [("100.00", "49.86"), ("100.01", "49.87"), ("0.01", "0.00"), ("1000000.00", "498630.14")],
)
def test_el_saldo_se_redondea_a_centavos(prima: str, esperado: str) -> None:
    periodo = PeriodoPagado(date(2026, 1, 1), date(2026, 12, 31), Decimal(prima))

    saldo, _, _ = calcular_saldo([periodo], date(2026, 7, 2))

    assert saldo == Decimal(esperado)  # x 182 / 365


def test_no_se_cancela_una_poliza_ya_cancelada() -> None:
    cancelada = poliza(
        estado=EstadoRegistroPoliza.CANCELADA,
        cancelada_en=datetime(2026, 5, 1, 15, 0, tzinfo=timezone.utc),
    )

    propuesta = proponer_cancelacion(cancelada, HOY)

    assert propuesta.cancelable is False
    assert [b.codigo for b in propuesta.bloqueos] == [CodigoBloqueo.POLIZA_NO_VIGENTE]
    assert "ya está cancelada" in propuesta.bloqueos[0].mensaje
    assert propuesta.saldo_estimado == Decimal("0.00")
    assert propuesta.dias_no_transcurridos == 0


def test_no_se_cancela_una_poliza_vencida() -> None:
    propuesta = proponer_cancelacion(poliza(), date(2027, 1, 1))

    assert propuesta.cancelable is False
    assert propuesta.bloqueos[0].codigo is CodigoBloqueo.POLIZA_NO_VIGENTE
    assert "venció" in propuesta.bloqueos[0].mensaje


def test_un_siniestro_en_tramite_bloquea_la_cancelacion() -> None:
    propuesta = proponer_cancelacion(poliza(), HOY, ["SIN-1"])

    assert propuesta.cancelable is False
    bloqueo = propuesta.bloqueos[0]
    assert bloqueo.codigo is CodigoBloqueo.SINIESTRO_EN_TRAMITE
    assert bloqueo.siniestros == ("SIN-1",)
    assert "un siniestro en trámite" in bloqueo.mensaje
    assert "cuando se resuelva." in bloqueo.mensaje
    # El saldo se sigue mostrando: el cliente ve cuánto le corresponderá al poder cancelar.
    assert propuesta.saldo_estimado == Decimal("74794.52")


def test_varios_siniestros_se_informan_en_plural() -> None:
    propuesta = proponer_cancelacion(poliza(), HOY, ["SIN-1", "SIN-2"])

    assert propuesta.bloqueos[0].siniestros == ("SIN-1", "SIN-2")
    assert "2 siniestros en trámite" in propuesta.bloqueos[0].mensaje
    assert "cuando se resuelvan." in propuesta.bloqueos[0].mensaje


def test_si_la_poliza_no_esta_vigente_solo_se_informa_ese_motivo() -> None:
    propuesta = proponer_cancelacion(poliza(), date(2027, 1, 1), ["SIN-1"])

    assert [b.codigo for b in propuesta.bloqueos] == [CodigoBloqueo.POLIZA_NO_VIGENTE]


def test_las_consecuencias_incluyen_lo_que_pierde_y_lo_que_recibe() -> None:
    con_saldo = proponer_cancelacion(poliza(), HOY)
    sin_saldo = proponer_cancelacion(poliza(), date(2026, 12, 31))

    textos = " ".join(con_saldo.consecuencias)
    assert "termina hoy" in textos
    assert "definitiva" in textos
    assert "dejará de aparecer entre tus coberturas activas" in textos
    assert "saldo estimado a favor" in textos
    assert "pendiente de gestión" in textos
    assert "No hay saldo a favor" in " ".join(sin_saldo.consecuencias)


def test_el_catalogo_de_motivos_trae_codigo_y_etiqueta() -> None:
    motivos = proponer_cancelacion(poliza(), HOY).motivos

    assert {m.codigo for m in motivos} == set(MotivoCancelacion)
    assert all(m.etiqueta for m in motivos)
    assert {m.codigo.value: m.etiqueta for m in motivos}["OTRO"] == "Otro motivo"


def test_la_solicitud_no_acepta_campos_ni_motivos_desconocidos() -> None:
    with pytest.raises(ValidationError):
        SolicitudCancelacion(motivo="PORQUE_SI", confirmo=True)
    with pytest.raises(ValidationError):
        SolicitudCancelacion(motivo=MotivoCancelacion.OTRO, confirmo=True, extra="x")
    with pytest.raises(ValidationError):
        SolicitudCancelacion(motivo=MotivoCancelacion.OTRO, confirmo=True, detalle="x" * 301)


def test_confirmar_es_falso_por_defecto() -> None:
    assert SolicitudCancelacion(motivo=MotivoCancelacion.OTRO).confirmo is False
