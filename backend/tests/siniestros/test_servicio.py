"""Pruebas unitarias del caso de uso de registro manual (HU20).

Complementan las de API: ejercitan directamente `ServicioSiniestros` y todas las ramas de
`_validar_fecha_evento` (fecha válida, futura, antes del inicio y después del fin).
"""

from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest

from app.polizas.dominio.modelos import (
    CoberturaPoliza,
    EstadoRegistroPoliza,
    Poliza,
    RamoPoliza,
)
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from app.siniestros.modelos import SolicitudSiniestro
from app.siniestros.repositorio import RepositorioSiniestrosEnMemoria
from app.siniestros.servicio import (
    FechaEventoInvalida,
    PolizaAjena,
    PolizaNoEncontrada,
    PolizaNoVigente,
    ServicioSiniestros,
)

AHORA = datetime(2026, 10, 21, 15, 0, tzinfo=UTC)  # 2026-10-21 en Bogotá


def _poliza(**cambios) -> Poliza:
    datos = {
        "poliza_id": "POL-1",
        "numero_poliza": "SOL-VI-000001",
        "cliente_id": "CLI-001",
        "ramo": RamoPoliza.VIAJE,
        "titular_nombre": "Ana Pérez",
        "titular_tipo_documento": "CC",
        "titular_numero_documento": "1012345678",
        "fecha_inicio": date(2026, 10, 1),
        "fecha_fin": date(2026, 12, 31),
        "prima_total": Decimal("85000.00"),
        "cobertura_principal": CoberturaPoliza(
            codigo="ASISTENCIA",
            nombre="Asistencia médica en viaje",
            suma_asegurada=Decimal("40000000.00"),
        ),
        "codigo_verificacion": "a1b2c3d4e5f60718",
        "emitida_en": datetime(2026, 9, 30, tzinfo=UTC),
    }
    datos.update(cambios)
    return Poliza(**datos)


_SIN_POLIZA = object()


def _servicio(poliza=_SIN_POLIZA):
    polizas = RepositorioPolizasEnMemoria()
    poliza_a_usar = _poliza() if poliza is _SIN_POLIZA else poliza
    if poliza_a_usar is not None:
        polizas.guardar(poliza_a_usar)
    siniestros = RepositorioSiniestrosEnMemoria()
    servicio = ServicioSiniestros(
        siniestros, polizas, reloj=lambda: AHORA, generar_id=lambda: "SIN-FIJO"
    )
    return servicio, siniestros


def _solicitud(**cambios) -> SolicitudSiniestro:
    datos = {
        "poliza_id": "POL-1",
        "fecha_evento": date(2026, 10, 20),
        "hora_evento": time(18, 30),
        "lugar": "Aeropuerto El Dorado",
        "descripcion": "El vuelo fue cancelado y hubo gastos adicionales.",
        "estimacion_danos": Decimal("850000.00"),
    }
    datos.update(cambios)
    return SolicitudSiniestro(**datos)


def test_registro_valido_persiste_y_fija_cliente_y_origen():
    servicio, siniestros = _servicio()

    creado = servicio.registrar_manual("CLI-001", "CLI-001", _solicitud())

    assert creado.siniestro_id == "SIN-FIJO"
    assert creado.cliente_id == "CLI-001"
    assert creado.origen.value == "MANUAL"
    assert creado.moneda == "COP"
    assert siniestros.obtener("SIN-FIJO") is not None


def test_poliza_inexistente():
    servicio, _ = _servicio(poliza=None)
    with pytest.raises(PolizaNoEncontrada):
        servicio.registrar_manual("CLI-001", "CLI-001", _solicitud())


def test_poliza_de_otro_titular():
    servicio, _ = _servicio(_poliza(cliente_id="OTRO"))
    with pytest.raises(PolizaAjena):
        servicio.registrar_manual("CLI-001", "CLI-001", _solicitud())


def test_poliza_cancelada():
    servicio, _ = _servicio(
        _poliza(
            estado=EstadoRegistroPoliza.CANCELADA, cancelada_en=datetime(2026, 10, 2, tzinfo=UTC)
        )
    )
    with pytest.raises(PolizaNoVigente):
        servicio.registrar_manual("CLI-001", "CLI-001", _solicitud())


def test_fecha_futura():
    servicio, _ = _servicio()
    with pytest.raises(FechaEventoInvalida) as exc:
        servicio.registrar_manual("CLI-001", "CLI-001", _solicitud(fecha_evento=date(2026, 10, 22)))
    assert exc.value.codigo == "FECHA_FUTURA"


def test_fecha_antes_del_inicio():
    servicio, _ = _servicio()
    with pytest.raises(FechaEventoInvalida) as exc:
        servicio.registrar_manual("CLI-001", "CLI-001", _solicitud(fecha_evento=date(2026, 9, 15)))
    assert exc.value.codigo == "FECHA_FUERA_DE_VIGENCIA"


def test_fecha_despues_del_fin_con_poliza_que_sigue_vigente():
    # La póliza vence el 2026-12-31 (futuro respecto a hoy=2026-10-21), así que sigue VIGENTE,
    # pero el evento del 2026-11-30 es posterior a hoy -> FECHA_FUTURA (se valida antes del fin).
    servicio, _ = _servicio()
    with pytest.raises(FechaEventoInvalida) as exc:
        servicio.registrar_manual("CLI-001", "CLI-001", _solicitud(fecha_evento=date(2026, 11, 30)))
    assert exc.value.codigo == "FECHA_FUTURA"


def test_fecha_posterior_al_fin_dentro_de_hoy():
    # Póliza corta que vence antes de hoy pero sigue "vigente" en el registro (no cancelada):
    # para aislar la rama `> fin` usamos una póliza cuyo fin es anterior a hoy y un evento
    # entre el fin y hoy. Como la póliza ya venció, primero se rechaza por vigencia (409).
    servicio, _ = _servicio(_poliza(fecha_inicio=date(2026, 9, 1), fecha_fin=date(2026, 10, 10)))
    with pytest.raises(PolizaNoVigente):
        servicio.registrar_manual("CLI-001", "CLI-001", _solicitud(fecha_evento=date(2026, 10, 15)))


def test_validar_fecha_evento_directo_cubre_rama_despues_del_fin():
    # Prueba directa del validador estático: fecha dentro de [hoy] pero posterior al fin.
    with pytest.raises(FechaEventoInvalida) as exc:
        ServicioSiniestros._validar_fecha_evento(
            fecha_evento=date(2026, 10, 20),
            inicio=date(2026, 10, 1),
            fin=date(2026, 10, 10),
            hoy=date(2026, 10, 21),
        )
    assert exc.value.codigo == "FECHA_FUERA_DE_VIGENCIA"


def test_validar_fecha_evento_directo_fecha_valida_no_lanza():
    # Rama feliz: ni futura ni fuera de vigencia -> no lanza (alcanza el exit).
    ServicioSiniestros._validar_fecha_evento(
        fecha_evento=date(2026, 10, 20),
        inicio=date(2026, 10, 1),
        fin=date(2026, 12, 31),
        hoy=date(2026, 10, 21),
    )
