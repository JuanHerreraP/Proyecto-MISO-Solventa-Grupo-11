"""Mensajes de los eventos que generan notificaciones."""

from decimal import Decimal

import pytest

from app.notificaciones.eventos import (
    estado_siniestro,
    formatear_monto,
    pago_parametrico,
    vencimiento_poliza,
)
from app.notificaciones.modelos import TipoNotificacion
from app.siniestros.modelos import EstadoSiniestro, OrigenSiniestro
from tests.billetera.fabrica import poliza
from tests.desembolsos.fabrica import siniestro


@pytest.mark.parametrize(
    ("monto", "esperado"),
    [
        (Decimal("150000"), "$150.000 COP"),
        (Decimal("150000.00"), "$150.000 COP"),
        (Decimal("24500.50"), "$24.500,50 COP"),
        (Decimal("1234567.89"), "$1.234.567,89 COP"),
        (Decimal("999"), "$999 COP"),
        (Decimal("1000"), "$1.000 COP"),
        (Decimal("0.5"), "$0,50 COP"),
        (Decimal("100.005"), "$100,01 COP"),
    ],
)
def test_formatea_el_monto_como_en_las_apps(monto, esperado) -> None:
    assert formatear_monto(monto, "COP") == esperado


def test_el_pago_parametrico_lleva_el_monto_la_poliza_y_el_destino() -> None:
    s = siniestro(
        origen=OrigenSiniestro.AUTOMATICO,
        estado=EstadoSiniestro.APROBADO,
        monto_aprobado=Decimal("500000.00"),
    )

    evento = pago_parametrico(s, poliza(numero_poliza="SOL-PM-000001"))

    assert evento.tipo is TipoNotificacion.PAGO_PARAMETRICO
    assert evento.clave == "PAGO_PARAMETRICO:SIN-1"
    assert evento.cuerpo == "Se aprobó un pago de $500.000 COP por tu póliza SOL-PM-000001."
    assert evento.datos == {
        "siniestro_id": "SIN-1",
        "poliza_id": "POL-1",
        "numero_poliza": "SOL-PM-000001",
        "estado": "APROBADO",
        "monto": "500000.00",
        "moneda": "COP",
    }


def test_sin_monto_aprobado_el_pago_usa_la_estimacion() -> None:
    s = siniestro(estimacion_danos=Decimal("300000.00"))

    assert "$300.000 COP" in pago_parametrico(s, None).cuerpo


def test_sin_la_poliza_el_mensaje_usa_su_identificador() -> None:
    evento = pago_parametrico(siniestro(), None)

    assert "póliza POL-1" in evento.cuerpo
    assert evento.datos["numero_poliza"] == "POL-1"


def test_un_siniestro_aprobado_dice_el_monto_y_su_clave_incluye_el_estado() -> None:
    s = siniestro(estado=EstadoSiniestro.APROBADO, monto_aprobado=Decimal("850000.00"))

    evento = estado_siniestro(s, poliza(numero_poliza="SOL-VI-000001"))

    assert evento.tipo is TipoNotificacion.ESTADO_SINIESTRO
    assert evento.clave == "ESTADO_SINIESTRO:SIN-1:APROBADO"
    assert evento.titulo == "Tu siniestro fue aprobado"
    assert evento.cuerpo == "Aprobamos tu siniestro de la póliza SOL-VI-000001 por $850.000 COP."
    assert evento.datos["siniestro_id"] == "SIN-1" and evento.datos["estado"] == "APROBADO"


def test_un_siniestro_rechazado_manda_al_detalle_para_ver_el_motivo() -> None:
    s = siniestro(estado=EstadoSiniestro.RECHAZADO, motivo_rechazo="Fuera de cobertura")

    evento = estado_siniestro(s, poliza(numero_poliza="SOL-VI-000001"))

    assert evento.clave == "ESTADO_SINIESTRO:SIN-1:RECHAZADO"
    assert evento.titulo == "Tu siniestro fue rechazado"
    assert "Consulta el detalle para ver el motivo" in evento.cuerpo
    # El motivo puede ser largo y sensible: no viaja en la notificación.
    assert "Fuera de cobertura" not in evento.cuerpo


def test_un_siniestro_en_evaluacion_lo_dice_en_lenguaje_del_cliente() -> None:
    s = siniestro(estado=EstadoSiniestro.EN_EVALUACION)

    evento = estado_siniestro(s, poliza(numero_poliza="SOL-VI-000001"))

    assert evento.titulo == "Tu siniestro está en evaluación"
    assert evento.cuerpo == "Estamos evaluando tu siniestro de la póliza SOL-VI-000001."
    assert evento.clave == "ESTADO_SINIESTRO:SIN-1:EN_EVALUACION"
    assert evento.datos["estado"] == "EN_EVALUACION"


def test_un_siniestro_registrado_confirma_la_recepcion() -> None:
    s = siniestro(estado=EstadoSiniestro.REGISTRADO)

    evento = estado_siniestro(s, poliza(numero_poliza="SOL-VI-000001"))

    assert evento.titulo == "Recibimos tu siniestro"
    assert evento.cuerpo == "Registramos tu siniestro de la póliza SOL-VI-000001."


def test_ningun_mensaje_de_estado_muestra_el_codigo_interno() -> None:
    for estado in EstadoSiniestro:
        evento = estado_siniestro(siniestro(estado=estado), None)

        assert estado.value not in evento.titulo
        assert estado.value not in evento.cuerpo


def test_un_aprobado_sin_monto_no_inventa_uno() -> None:
    s = siniestro(estado=EstadoSiniestro.APROBADO, monto_aprobado=None)

    assert "por $" not in estado_siniestro(s, None).cuerpo


def test_el_vencimiento_lleva_la_poliza_los_dias_y_lleva_a_renovar() -> None:
    p = poliza(poliza_id="POL-9", numero_poliza="SOL-VD-000009")

    evento = vencimiento_poliza(p, 15)

    assert evento.tipo is TipoNotificacion.VENCIMIENTO_POLIZA
    assert evento.titulo == "Tu póliza está por vencer"
    assert evento.cuerpo == (
        "Tu póliza SOL-VD-000009 vence en 15 días. Renuévala para mantener tu cobertura."
    )
    assert evento.datos == {
        "poliza_id": "POL-9",
        "numero_poliza": "SOL-VD-000009",
        "dias": "15",
        "fecha_fin": "2026-12-31",
    }


def test_la_clave_del_vencimiento_distingue_el_aviso_y_la_fecha_de_fin() -> None:
    p = poliza()

    quince = vencimiento_poliza(p, 15).clave
    tres = vencimiento_poliza(p, 3).clave
    renovada = vencimiento_poliza(
        p.model_copy(update={"fecha_fin": p.fecha_fin.replace(year=2027)}), 15
    )

    assert len({quince, tres, renovada.clave}) == 3
    assert quince == "VENCIMIENTO:POL-1:2026-12-31:15"


def test_a_un_dia_dice_manana() -> None:
    assert "vence mañana" in vencimiento_poliza(poliza(), 1).cuerpo
