"""Reglas de la renovación automática: ventana, día del cobro e idempotencia (HU17)."""

from datetime import date

from app.polizas.dominio.modelos import EstadoRegistroPoliza, RamoPoliza
from app.polizas.dominio.renovacion_automatica import (
    candidata,
    ciclo_id_de,
    llave_cobro,
    preaviso_desde,
    toca_cobrar,
)
from tests.renovacion_automatica.fabrica import CAIDA, RECHAZADA, TARJETA
from tests.renovaciones.fabrica import AHORA, poliza


def test_la_ventana_de_preaviso_empieza_30_dias_antes_del_vencimiento() -> None:
    vida = poliza()

    assert preaviso_desde(vida) == date(2026, 12, 1)
    assert not candidata(vida, date(2026, 11, 30))
    assert candidata(vida, date(2026, 12, 1))
    assert candidata(vida, date(2026, 12, 31))
    assert not candidata(vida, date(2027, 1, 1))  # Ya venció.


def test_solo_son_candidatas_las_vigentes_que_se_renuevan_y_no_estan_renovadas() -> None:
    hoy = date(2026, 12, 10)

    assert not candidata(poliza(ramo=RamoPoliza.VIAJE), hoy)
    assert not candidata(poliza(estado=EstadoRegistroPoliza.CANCELADA, cancelada_en=AHORA), hoy)
    # Renovada por adelantado: el nuevo periodo aún no empieza.
    assert not candidata(poliza(fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 1, 5)), hoy)


def test_se_cobra_el_ultimo_dia_de_la_vigencia() -> None:
    vida = poliza()

    assert not toca_cobrar(vida, date(2026, 12, 30))
    assert toca_cobrar(vida, date(2026, 12, 31))


def test_un_ciclo_por_periodo() -> None:
    assert ciclo_id_de("POL-1", date(2026, 12, 31)) == "AUT-POL-1-20261231"


def test_la_llave_del_cobro_cambia_con_la_tarjeta_y_cabe_en_el_pago() -> None:
    llaves = {llave_cobro("COT-1", medio) for medio in (TARJETA, RECHAZADA, CAIDA)}

    assert len(llaves) == 3
    assert llave_cobro("COT-1", TARJETA) == llave_cobro("COT-1", TARJETA)
    assert llave_cobro("COT-1", TARJETA) != llave_cobro("COT-2", TARJETA)
    assert all(len(llave) <= 64 for llave in llaves)
