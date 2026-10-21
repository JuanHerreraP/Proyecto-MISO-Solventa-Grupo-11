from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.polizas.dominio.modelos import EstadoPoliza, EstadoRegistroPoliza, hoy_en_colombia
from tests.billetera.fabrica import HOY, poliza


def test_una_poliza_dentro_de_su_vigencia_esta_vigente():
    assert poliza().estado_en(HOY) is EstadoPoliza.VIGENTE


def test_el_ultimo_dia_de_vigencia_la_poliza_sigue_vigente():
    assert poliza(fecha_fin=HOY).estado_en(HOY) is EstadoPoliza.VIGENTE


def test_despues_de_la_fecha_de_fin_la_poliza_esta_vencida():
    vencida = poliza(fecha_inicio=date(2025, 1, 1), fecha_fin=date(2025, 12, 31))
    assert vencida.estado_en(HOY) is EstadoPoliza.VENCIDA


def test_una_poliza_cancelada_queda_cancelada_aunque_su_vigencia_no_termine():
    cancelada = poliza(estado=EstadoRegistroPoliza.CANCELADA)
    assert cancelada.estado_en(HOY) is EstadoPoliza.CANCELADA


def test_la_fecha_de_fin_no_puede_ser_anterior_a_la_de_inicio():
    with pytest.raises(ValidationError):
        poliza(fecha_inicio=date(2026, 12, 1), fecha_fin=date(2026, 11, 1))


def test_cancelada_y_fecha_de_cancelacion_van_juntas():
    with pytest.raises(ValidationError):
        poliza(cancelada_en=datetime(2026, 10, 10, tzinfo=UTC))


def test_el_documento_del_titular_se_muestra_enmascarado():
    assert poliza().documento_enmascarado == "CC ****5678"


def test_el_qr_lleva_el_numero_de_poliza_y_el_codigo_de_verificacion():
    assert poliza().contenido_qr == "SOLVENTA|SOL-VI-000001|a1b2c3d4e5f60718"


def test_el_dia_se_calcula_en_hora_de_colombia():
    # 02:00 UTC del 22 todavía es el 21 en Bogotá.
    assert hoy_en_colombia(datetime(2026, 10, 22, 2, 0, tzinfo=UTC)) == date(2026, 10, 21)
    assert hoy_en_colombia(datetime(2026, 10, 22, 2, 0)) == date(2026, 10, 21)
