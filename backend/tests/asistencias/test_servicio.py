"""Pruebas unitarias del caso de uso de asistencia (HU06)."""

from datetime import UTC, datetime

import pytest

from app.asistencias.modelos import (
    EstadoAsistencia,
    NuevaAsistencia,
    TipoServicioAsistencia,
)
from app.asistencias.repositorio import (
    RepositorioAsistenciasEnMemoria,
    RepositorioPrestadoresEnMemoria,
)
from app.asistencias.servicio import (
    AsistenciaAjena,
    AsistenciaNoEncontrada,
    AsistenciaYaCancelada,
    PolizaAjena,
    PolizaNoEncontrada,
    PolizaNoVigente,
    PrestadorNoDisponible,
    PrestadorNoEncontrado,
    RadioInvalido,
    ServicioAsistencias,
    ServicioNoDisponible,
    ServicioNoOfrecidoPorPrestador,
)
from app.polizas.dominio.modelos import EstadoRegistroPoliza, RamoPoliza
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from tests.asistencias.fabrica import BOGOTA, MEDELLIN, MOSQUERA, prestador
from tests.billetera.fabrica import poliza

AHORA = datetime(2026, 10, 21, 15, 0, tzinfo=UTC)  # 2026-10-21 en Bogotá
REPARACION = TipoServicioAsistencia.REPARACION_DISPOSITIVO
MEDICA = TipoServicioAsistencia.ASISTENCIA_MEDICA

# La póliza por defecto de la fábrica es VIAJE; para dispositivos se cambia el ramo.
POLIZA_DISPOSITIVOS = dict(ramo=RamoPoliza.PROTECCION_DISPOSITIVOS)


def _servicio(polizas=None, prestadores=None):
    repo_polizas = RepositorioPolizasEnMemoria()
    if polizas is None:
        repo_polizas.guardar(poliza(**POLIZA_DISPOSITIVOS))
    else:
        for p in polizas:
            repo_polizas.guardar(p)
    repo_prestadores = RepositorioPrestadoresEnMemoria()
    for pr in prestadores or []:
        repo_prestadores.guardar(pr)
    repo_asistencias = RepositorioAsistenciasEnMemoria()
    servicio = ServicioAsistencias(
        prestadores=repo_prestadores,
        asistencias=repo_asistencias,
        polizas=repo_polizas,
        reloj=lambda: AHORA,
        generar_id=lambda: "ASI-FIJO",
    )
    return servicio, repo_asistencias


# --- prestadores cercanos ---------------------------------------------------------------


def test_cercanos_incluye_compatibles_y_los_ordena_por_distancia():
    servicio, _ = _servicio(
        prestadores=[
            prestador(prestador_id="LEJOS", latitud=MOSQUERA[0], longitud=MOSQUERA[1]),
            prestador(prestador_id="CERCA", latitud=4.7150, longitud=-74.0690),
        ]
    )
    cercanos = servicio.prestadores_cercanos("CLI-001", "POL-1", REPARACION, *BOGOTA, radio_km=25)
    assert [c.prestador.prestador_id for c in cercanos] == ["CERCA", "LEJOS"]
    assert cercanos[0].distancia < cercanos[1].distancia


def test_cercanos_excluye_prestador_incompatible():
    servicio, _ = _servicio(
        prestadores=[
            prestador(prestador_id="SOLO_VIAJE", servicios=[MEDICA]),
            prestador(prestador_id="OK"),
        ]
    )
    cercanos = servicio.prestadores_cercanos("CLI-001", "POL-1", REPARACION, *BOGOTA, radio_km=25)
    assert [c.prestador.prestador_id for c in cercanos] == ["OK"]


def test_cercanos_excluye_prestador_inactivo():
    servicio, _ = _servicio(
        prestadores=[
            prestador(prestador_id="INACTIVO", activo=False),
            prestador(prestador_id="OK"),
        ]
    )
    cercanos = servicio.prestadores_cercanos("CLI-001", "POL-1", REPARACION, *BOGOTA, radio_km=25)
    assert [c.prestador.prestador_id for c in cercanos] == ["OK"]


def test_cercanos_excluye_prestador_fuera_del_radio():
    servicio, _ = _servicio(
        prestadores=[
            prestador(prestador_id="MEDELLIN", latitud=MEDELLIN[0], longitud=MEDELLIN[1]),
            prestador(prestador_id="CERCA"),
        ]
    )
    cercanos = servicio.prestadores_cercanos("CLI-001", "POL-1", REPARACION, *BOGOTA, radio_km=25)
    assert [c.prestador.prestador_id for c in cercanos] == ["CERCA"]


def test_cercanos_lista_vacia_no_es_error():
    servicio, _ = _servicio(prestadores=[])
    assert servicio.prestadores_cercanos("CLI-001", "POL-1", REPARACION, *BOGOTA, radio_km=25) == []


def test_cercanos_radio_fuera_de_rango():
    servicio, _ = _servicio(prestadores=[prestador()])
    with pytest.raises(RadioInvalido):
        servicio.prestadores_cercanos("CLI-001", "POL-1", REPARACION, *BOGOTA, radio_km=0.5)
    with pytest.raises(RadioInvalido):
        servicio.prestadores_cercanos("CLI-001", "POL-1", REPARACION, *BOGOTA, radio_km=101)


def test_cercanos_servicio_incompatible_con_ramo():
    servicio, _ = _servicio(prestadores=[prestador()])
    # La póliza es de dispositivos: pedir asistencia médica es incompatible con el ramo.
    with pytest.raises(ServicioNoDisponible):
        servicio.prestadores_cercanos("CLI-001", "POL-1", MEDICA, *BOGOTA, radio_km=25)


def test_cercanos_poliza_ajena():
    servicio, _ = _servicio(
        polizas=[poliza(cliente_id="OTRO", **POLIZA_DISPOSITIVOS)],
        prestadores=[prestador()],
    )
    with pytest.raises(PolizaAjena):
        servicio.prestadores_cercanos("CLI-001", "POL-1", REPARACION, *BOGOTA, radio_km=25)


def test_cercanos_poliza_inexistente():
    servicio, _ = _servicio(polizas=[], prestadores=[prestador()])
    with pytest.raises(PolizaNoEncontrada):
        servicio.prestadores_cercanos("CLI-001", "POL-1", REPARACION, *BOGOTA, radio_km=25)


def test_cercanos_poliza_vencida():
    vencida = poliza(
        fecha_inicio=datetime(2024, 1, 1).date(),
        fecha_fin=datetime(2024, 12, 31).date(),
        **POLIZA_DISPOSITIVOS,
    )
    servicio, _ = _servicio(polizas=[vencida], prestadores=[prestador()])
    with pytest.raises(PolizaNoVigente):
        servicio.prestadores_cercanos("CLI-001", "POL-1", REPARACION, *BOGOTA, radio_km=25)


# --- crear ------------------------------------------------------------------------------


def _nueva(**cambios) -> NuevaAsistencia:
    datos = {
        "poliza_id": "POL-1",
        "prestador_id": "PREST-TEC-001",
        "servicio": REPARACION,
        "latitud": BOGOTA[0],
        "longitud": BOGOTA[1],
        "observaciones": "El dispositivo no enciende.",
    }
    datos.update(cambios)
    return NuevaAsistencia(**datos)


def test_crear_fija_cliente_estado_y_fecha():
    servicio, repo = _servicio(prestadores=[prestador()])
    asistencia, prestador_usado = servicio.crear("CLI-001", _nueva())
    assert asistencia.asistencia_id == "ASI-FIJO"
    assert asistencia.cliente_id == "CLI-001"
    assert asistencia.estado is EstadoAsistencia.SOLICITADA
    assert asistencia.creada_en == AHORA
    assert asistencia.cancelada_en is None
    assert prestador_usado.prestador_id == "PREST-TEC-001"
    assert repo.obtener("ASI-FIJO") is not None


def test_crear_servicio_no_permitido_por_ramo():
    # La póliza de viaje no ofrece reparación de dispositivos.
    servicio, _ = _servicio(polizas=[poliza()], prestadores=[prestador()])
    with pytest.raises(ServicioNoDisponible):
        servicio.crear("CLI-001", _nueva())


def test_crear_prestador_inexistente():
    servicio, _ = _servicio(prestadores=[])
    with pytest.raises(PrestadorNoEncontrado):
        servicio.crear("CLI-001", _nueva())


def test_crear_prestador_inactivo():
    servicio, _ = _servicio(prestadores=[prestador(activo=False)])
    with pytest.raises(PrestadorNoDisponible):
        servicio.crear("CLI-001", _nueva())


def test_crear_prestador_no_ofrece_el_servicio():
    servicio, _ = _servicio(
        prestadores=[prestador(servicios=[TipoServicioAsistencia.DIAGNOSTICO_TECNICO])]
    )
    with pytest.raises(ServicioNoOfrecidoPorPrestador):
        servicio.crear("CLI-001", _nueva(servicio=REPARACION))


def test_crear_poliza_ajena():
    servicio, _ = _servicio(
        polizas=[poliza(cliente_id="OTRO", **POLIZA_DISPOSITIVOS)],
        prestadores=[prestador()],
    )
    with pytest.raises(PolizaAjena):
        servicio.crear("CLI-001", _nueva())


# --- cancelar ---------------------------------------------------------------------------


def test_cancelar_marca_estado_y_fecha():
    servicio, repo = _servicio(prestadores=[prestador()])
    servicio.crear("CLI-001", _nueva())
    cancelada = servicio.cancelar("CLI-001", "ASI-FIJO")
    assert cancelada.estado is EstadoAsistencia.CANCELADA
    assert cancelada.cancelada_en == AHORA
    # No se elimina: sigue existiendo en el repositorio.
    assert repo.obtener("ASI-FIJO").estado is EstadoAsistencia.CANCELADA


def test_cancelar_asistencia_de_otro_cliente():
    servicio, _ = _servicio(prestadores=[prestador()])
    servicio.crear("CLI-001", _nueva())
    with pytest.raises(AsistenciaAjena):
        servicio.cancelar("OTRO", "ASI-FIJO")


def test_cancelar_asistencia_inexistente():
    servicio, _ = _servicio(prestadores=[prestador()])
    with pytest.raises(AsistenciaNoEncontrada):
        servicio.cancelar("CLI-001", "ASI-NO")


def test_cancelar_asistencia_ya_cancelada():
    servicio, _ = _servicio(prestadores=[prestador()])
    servicio.crear("CLI-001", _nueva())
    servicio.cancelar("CLI-001", "ASI-FIJO")
    with pytest.raises(AsistenciaYaCancelada):
        servicio.cancelar("CLI-001", "ASI-FIJO")


def test_listar_devuelve_solo_las_del_cliente():
    servicio, _ = _servicio(
        polizas=[
            poliza(**POLIZA_DISPOSITIVOS),
            poliza(
                poliza_id="POL-2",
                cliente_id="OTRO",
                numero_poliza="SOL-DP-2",
                **POLIZA_DISPOSITIVOS,
            ),
        ],
        prestadores=[prestador()],
    )
    servicio.crear("CLI-001", _nueva())
    propias = servicio.listar_de_cliente("CLI-001")
    assert [a.asistencia_id for a in propias] == ["ASI-FIJO"]
    assert servicio.listar_de_cliente("OTRO") == []


def test_poliza_cancelada_no_permite_crear():
    cancelada = poliza(estado=EstadoRegistroPoliza.CANCELADA, **POLIZA_DISPOSITIVOS)
    servicio, _ = _servicio(polizas=[cancelada], prestadores=[prestador()])
    with pytest.raises(PolizaNoVigente):
        servicio.crear("CLI-001", _nueva())


# --- operaciones: aceptación y seguimiento (HU06 ampliación) ----------------------------


def _aceptacion(**cambios):
    from app.asistencias.modelos import AceptacionAsistencia

    return AceptacionAsistencia(**cambios)


def _seguimiento(**cambios):
    from app.asistencias.modelos import SeguimientoAsistencia

    return SeguimientoAsistencia(**cambios)


def test_aceptar_sin_eta_pasa_a_aceptada_y_fija_fecha():
    servicio, repo = _servicio(prestadores=[prestador()])
    servicio.crear("CLI-001", _nueva())
    aceptada = servicio.aceptar("ASI-FIJO", _aceptacion())
    assert aceptada.estado is EstadoAsistencia.ACEPTADA
    assert aceptada.aceptada_en == AHORA
    assert aceptada.tiempo_estimado_llegada_minutos is None
    assert repo.obtener("ASI-FIJO").estado is EstadoAsistencia.ACEPTADA


def test_aceptar_con_eta_lo_registra():
    servicio, _ = _servicio(prestadores=[prestador()])
    servicio.crear("CLI-001", _nueva())
    aceptada = servicio.aceptar("ASI-FIJO", _aceptacion(tiempo_estimado_llegada_minutos=20))
    assert aceptada.tiempo_estimado_llegada_minutos == 20


def test_aceptar_dos_veces_falla():
    from app.asistencias.servicio import AsistenciaYaAceptada

    servicio, _ = _servicio(prestadores=[prestador()])
    servicio.crear("CLI-001", _nueva())
    servicio.aceptar("ASI-FIJO", _aceptacion())
    with pytest.raises(AsistenciaYaAceptada):
        servicio.aceptar("ASI-FIJO", _aceptacion())


def test_aceptar_cancelada_falla():
    from app.asistencias.servicio import AsistenciaCancelada

    servicio, _ = _servicio(prestadores=[prestador()])
    servicio.crear("CLI-001", _nueva())
    servicio.cancelar("CLI-001", "ASI-FIJO")
    with pytest.raises(AsistenciaCancelada):
        servicio.aceptar("ASI-FIJO", _aceptacion())


def test_aceptar_inexistente_falla():
    servicio, _ = _servicio(prestadores=[prestador()])
    with pytest.raises(AsistenciaNoEncontrada):
        servicio.aceptar("ASI-NO", _aceptacion())


def test_actualizar_eta_requiere_aceptada():
    from app.asistencias.servicio import TransicionEstadoInvalida

    servicio, _ = _servicio(prestadores=[prestador()])
    servicio.crear("CLI-001", _nueva())
    with pytest.raises(TransicionEstadoInvalida):
        servicio.actualizar_seguimiento(
            "ASI-FIJO", _seguimiento(tiempo_estimado_llegada_minutos=15)
        )


def test_actualizar_eta_en_aceptada():
    servicio, _ = _servicio(prestadores=[prestador()])
    servicio.crear("CLI-001", _nueva())
    servicio.aceptar("ASI-FIJO", _aceptacion())
    actualizada = servicio.actualizar_seguimiento(
        "ASI-FIJO", _seguimiento(tiempo_estimado_llegada_minutos=15)
    )
    assert actualizada.tiempo_estimado_llegada_minutos == 15


def test_listar_para_operaciones_filtra_por_estado():
    servicio, _ = _servicio(prestadores=[prestador()])
    servicio.crear("CLI-001", _nueva())
    servicio.aceptar("ASI-FIJO", _aceptacion())
    aceptadas = servicio.listar_para_operaciones(estado=EstadoAsistencia.ACEPTADA)
    assert [a.asistencia_id for a in aceptadas] == ["ASI-FIJO"]
    assert servicio.listar_para_operaciones(estado=EstadoAsistencia.SOLICITADA) == []
