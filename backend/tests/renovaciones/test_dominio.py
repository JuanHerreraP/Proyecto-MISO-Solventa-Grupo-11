"""Reglas de la renovación: ventana, ramos, nueva vigencia y estados (HU22)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.polizas.dominio.modelos import EstadoRegistroPoliza, RamoPoliza
from app.polizas.dominio.renovacion import (
    CodigoBloqueoRenovacion,
    EstadoRenovacion,
    Renovacion,
    Vigencia,
    datos_de_renovacion,
    evaluar_bloqueos,
    nueva_vigencia,
    poliza_renovada,
    renovable_desde,
    renovacion_id_de,
)
from tests.renovaciones.fabrica import AHORA, HOY, poliza


def codigos(poliza_, hoy=HOY) -> list[CodigoBloqueoRenovacion]:
    return [b.codigo for b in evaluar_bloqueos(poliza_, hoy)]


def renovacion(**cambios) -> Renovacion:
    datos = {
        "renovacion_id": "REN-1",
        "poliza_id": "POL-VIDA-1",
        "cotizacion_id": "COT-REN-1",
        "anterior_inicio": date(2026, 1, 1),
        "anterior_fin": date(2026, 12, 31),
        "anterior_prima": Decimal("150000.00"),
        "nuevo_inicio": date(2027, 1, 1),
        "nuevo_fin": date(2027, 12, 31),
        "prima_principal": Decimal("420000.00"),
        "prima_opcionales": Decimal("0.00"),
        "prima_total": Decimal("420000.00"),
        "moneda": "COP",
        "vigente_hasta": AHORA + timedelta(days=7),
        "solicitado_por": "CLI-001",
        "rol_solicitante": "CLIENTE",
        "creado_en": AHORA,
    }
    datos.update(cambios)
    return Renovacion(**datos)


def test_una_poliza_vigente_dentro_de_la_ventana_se_puede_renovar() -> None:
    assert codigos(poliza()) == []


def test_la_ventana_abre_30_dias_antes_del_vencimiento() -> None:
    assert renovable_desde(poliza()) == date(2026, 12, 1)
    assert codigos(poliza(), date(2026, 12, 1)) == []
    assert codigos(poliza(), date(2026, 11, 30)) == [CodigoBloqueoRenovacion.FUERA_DE_VENTANA]
    # El último día de la póliza todavía se puede renovar.
    assert codigos(poliza(), date(2026, 12, 31)) == []


def test_fuera_de_la_ventana_se_informa_desde_cuando_se_puede() -> None:
    mensaje = evaluar_bloqueos(poliza(), date(2026, 6, 1))[0].mensaje

    assert "01/12/2026" in mensaje
    assert "30 días" in mensaje


@pytest.mark.parametrize(
    "ramo", [RamoPoliza.VIDA, RamoPoliza.PROTECCION_DISPOSITIVOS, RamoPoliza.PARAMETRICO]
)
def test_los_ramos_renovables(ramo) -> None:
    assert codigos(poliza(ramo=ramo)) == []


def test_el_seguro_de_viaje_no_se_renueva() -> None:
    bloqueos = evaluar_bloqueos(poliza(ramo=RamoPoliza.VIAJE), HOY)

    assert [b.codigo for b in bloqueos] == [CodigoBloqueoRenovacion.RAMO_NO_RENOVABLE]
    assert "Seguro de viaje" in bloqueos[0].mensaje


def test_una_poliza_vencida_no_se_renueva() -> None:
    bloqueos = evaluar_bloqueos(poliza(), date(2027, 1, 1))

    assert [b.codigo for b in bloqueos] == [CodigoBloqueoRenovacion.POLIZA_NO_VIGENTE]
    assert "venció" in bloqueos[0].mensaje


def test_una_poliza_cancelada_no_se_renueva() -> None:
    cancelada = poliza(
        estado=EstadoRegistroPoliza.CANCELADA,
        cancelada_en=datetime(2026, 12, 5, 15, 0, tzinfo=UTC),
    )

    bloqueos = evaluar_bloqueos(cancelada, HOY)

    assert [b.codigo for b in bloqueos] == [CodigoBloqueoRenovacion.POLIZA_NO_VIGENTE]
    assert "cancelada" in bloqueos[0].mensaje


def test_una_poliza_ya_renovada_con_anticipacion_no_se_vuelve_a_renovar() -> None:
    renovada = poliza_renovada(poliza(), renovacion())

    bloqueos = evaluar_bloqueos(renovada, HOY)

    assert [b.codigo for b in bloqueos] == [CodigoBloqueoRenovacion.YA_RENOVADA]
    assert "01/01/2027" in bloqueos[0].mensaje


def test_la_renovacion_continua_al_dia_siguiente_y_dura_los_meses_contratados() -> None:
    assert nueva_vigencia(poliza(), {"meses_cobertura": 12}) == Vigencia(
        inicio=date(2027, 1, 1), fin=date(2027, 12, 31)
    )
    assert nueva_vigencia(poliza(), {"meses_cobertura": 6}) == Vigencia(
        inicio=date(2027, 1, 1), fin=date(2027, 6, 30)
    )


def test_la_renovacion_por_meses_respeta_el_anio_bisiesto() -> None:
    anio_2027 = poliza(fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31))

    vigencia = nueva_vigencia(anio_2027, {"meses_cobertura": 12})

    assert vigencia == Vigencia(inicio=date(2028, 1, 1), fin=date(2028, 12, 31))


def test_sin_meses_la_renovacion_dura_los_mismos_dias() -> None:
    marzo = poliza(fecha_inicio=date(2026, 3, 1), fecha_fin=date(2026, 3, 31))  # 31 días

    vigencia = nueva_vigencia(marzo, {})

    assert vigencia == Vigencia(inicio=date(2026, 4, 1), fin=date(2026, 5, 1))
    assert (vigencia.fin - vigencia.inicio).days + 1 == 31


def test_los_meses_invalidos_se_ignoran() -> None:
    for meses in (0, -3, True, "12", 5000):
        vigencia = nueva_vigencia(poliza(), {"meses_cobertura": meses})
        assert vigencia == Vigencia(inicio=date(2027, 1, 1), fin=date(2027, 12, 31))


def test_las_fechas_del_periodo_de_los_datos_del_riesgo_se_actualizan() -> None:
    datos = {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-12-31", "valor_asegurado": "5"}
    vigencia = Vigencia(inicio=date(2027, 1, 1), fin=date(2027, 12, 31))

    nuevos = datos_de_renovacion(datos, vigencia)

    assert nuevos["fecha_inicio"] == "2027-01-01"
    assert nuevos["fecha_fin"] == "2027-12-31"
    assert nuevos["valor_asegurado"] == "5"
    assert datos["fecha_inicio"] == "2026-01-01"  # el original no se toca


def test_los_datos_sin_periodo_se_dejan_igual() -> None:
    datos = {"meses_cobertura": 12, "fumador": False}

    assert datos_de_renovacion(datos, Vigencia(inicio=HOY, fin=HOY)) == datos


def test_una_renovacion_sin_pagar_vence_con_su_cotizacion() -> None:
    r = renovacion()

    assert r.estado_en(AHORA) is EstadoRenovacion.PENDIENTE_PAGO
    assert r.pendiente_en(AHORA) is True
    assert r.estado_en(r.vigente_hasta) is EstadoRenovacion.VENCIDA
    assert r.pendiente_en(r.vigente_hasta) is False


def test_una_renovacion_aplicada_no_vence() -> None:
    r = renovacion(estado=EstadoRenovacion.APLICADA, aplicada_en=AHORA)

    assert r.estado_en(AHORA + timedelta(days=60)) is EstadoRenovacion.APLICADA


def test_poliza_renovada_conserva_numero_y_coberturas_y_toma_el_nuevo_periodo() -> None:
    original = poliza()

    renovada = poliza_renovada(original, renovacion(prima_total=Decimal("493000.00")))

    assert renovada.numero_poliza == original.numero_poliza
    assert renovada.poliza_id == original.poliza_id
    assert renovada.codigo_verificacion == original.codigo_verificacion
    assert renovada.cobertura_principal == original.cobertura_principal
    assert (renovada.fecha_inicio, renovada.fecha_fin) == (date(2027, 1, 1), date(2027, 12, 31))
    assert renovada.prima_total == Decimal("493000.00")
    assert original.fecha_fin == date(2026, 12, 31)  # la original no se modifica


def test_el_identificador_sale_de_la_poliza_y_del_periodo() -> None:
    assert renovacion_id_de("POL-1", date(2027, 1, 1)) == "REN-POL-1-20270101"
