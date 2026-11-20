"""Pruebas unitarias de la distancia Haversine y del catálogo de servicios por ramo (HU06)."""

from app.asistencias.modelos import (
    SERVICIOS_POR_RAMO,
    TipoServicioAsistencia,
    distancia_km,
    ramo_ofrece_servicio,
    servicios_del_ramo,
)
from app.polizas.dominio.modelos import RamoPoliza
from tests.asistencias.fabrica import BOGOTA, MEDELLIN, MOSQUERA


def test_distancia_cero_cuando_los_puntos_coinciden():
    assert distancia_km(*BOGOTA, *BOGOTA) == 0.0


def test_distancia_es_positiva_y_simetrica():
    ida = distancia_km(*BOGOTA, *MOSQUERA)
    vuelta = distancia_km(*MOSQUERA, *BOGOTA)
    assert ida > 0
    assert round(ida, 6) == round(vuelta, 6)


def test_distancia_bogota_mosquera_es_del_orden_esperado():
    # El centro de Bogotá y Mosquera están a ~17-18 km en línea recta.
    assert 15 < distancia_km(*BOGOTA, *MOSQUERA) < 20


def test_medellin_queda_muy_lejos_de_bogota():
    # Fuera de cualquier radio de HU06 (máximo 100 km).
    assert distancia_km(*BOGOTA, *MEDELLIN) > 200


def test_orden_por_cercania_es_consistente():
    cerca = distancia_km(*BOGOTA, 4.7150, -74.0690)
    lejos = distancia_km(*BOGOTA, *MOSQUERA)
    assert cerca < lejos


def test_viaje_ofrece_medica_y_viajero():
    assert servicios_del_ramo(RamoPoliza.VIAJE) == (
        TipoServicioAsistencia.ASISTENCIA_MEDICA,
        TipoServicioAsistencia.ASISTENCIA_VIAJERO,
    )


def test_proteccion_dispositivos_ofrece_diagnostico_y_reparacion():
    assert servicios_del_ramo(RamoPoliza.PROTECCION_DISPOSITIVOS) == (
        TipoServicioAsistencia.DIAGNOSTICO_TECNICO,
        TipoServicioAsistencia.REPARACION_DISPOSITIVO,
    )


def test_vida_no_ofrece_servicios():
    assert servicios_del_ramo(RamoPoliza.VIDA) == ()


def test_parametrico_no_ofrece_servicios():
    assert servicios_del_ramo(RamoPoliza.PARAMETRICO) == ()


def test_todos_los_ramos_estan_en_el_catalogo():
    assert set(SERVICIOS_POR_RAMO.keys()) == set(RamoPoliza)


def test_ramo_ofrece_servicio_valida_la_compatibilidad():
    assert ramo_ofrece_servicio(
        RamoPoliza.PROTECCION_DISPOSITIVOS, TipoServicioAsistencia.REPARACION_DISPOSITIVO
    )
    assert not ramo_ofrece_servicio(
        RamoPoliza.PROTECCION_DISPOSITIVOS, TipoServicioAsistencia.ASISTENCIA_MEDICA
    )
    assert not ramo_ofrece_servicio(RamoPoliza.VIDA, TipoServicioAsistencia.ASISTENCIA_MEDICA)
