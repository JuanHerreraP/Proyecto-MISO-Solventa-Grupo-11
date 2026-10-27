"""Pruebas unitarias de la lógica paramétrica de telemetría (HU20).

Cubre el parser de la condición, la conversión a Decimal, el emparejamiento (`_aplica`) y los
caminos del servicio que la API no ejercita (clima bajo umbral, tipo desconocido, umbral ausente).
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.polizas.dominio.modelos import (
    CoberturaPoliza,
    EstadoRegistroPoliza,
    Poliza,
    RamoPoliza,
)
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from app.siniestros.repositorio import RepositorioSiniestrosEnMemoria
from app.siniestros.telemetria import (
    EventoParametrico,
    ResultadoTelemetria,
    ServicioTelemetria,
    _a_decimal,
    parsear_condicion,
)

AHORA = datetime(2026, 10, 26, 20, 0, tzinfo=UTC)


# --- parsear_condicion -------------------------------------------------------------------


def test_parsear_condicion_vacia_o_none():
    assert parsear_condicion(None) == {}
    assert parsear_condicion("") == {}


def test_parsear_condicion_ignora_partes_sin_igual_y_claves_vacias():
    # "solo_texto" no tiene '='; "=valor" tiene la clave vacía. Ambos se descartan.
    condicion = parsear_condicion("solo_texto; =valor; numero_vuelo=AV123 ; UBICACION = BOG")
    assert condicion == {"numero_vuelo": "AV123", "ubicacion": "BOG"}


# --- _a_decimal --------------------------------------------------------------------------


@pytest.mark.parametrize("valor", [None, "abc", "", object()])
def test_a_decimal_invalido_devuelve_none(valor):
    assert _a_decimal(valor) is None


def test_a_decimal_valido():
    assert _a_decimal("180") == Decimal("180")


# --- _aplica -----------------------------------------------------------------------------


def _evento(tipo="RETRASO_VUELO", vuelo="AV123", ubicacion="BOG", valor="215"):
    return EventoParametrico(
        evento_id="E-1",
        tipo_evento=tipo,
        valor_observado=Decimal(valor),
        fecha_evento=AHORA,
        numero_vuelo=vuelo,
        ubicacion=ubicacion,
    )


def test_aplica_tipo_distinto_es_falso():
    condicion = {"tipo_evento": "EVENTO_CLIMATICO", "ubicacion": "BOG"}
    assert ServicioTelemetria._aplica(condicion, _evento(tipo="RETRASO_VUELO")) is False


def test_aplica_vuelo_que_no_coincide_es_falso():
    condicion = {"tipo_evento": "RETRASO_VUELO", "numero_vuelo": "LA999"}
    assert ServicioTelemetria._aplica(condicion, _evento(vuelo="AV123")) is False


def test_aplica_clima_coincide_por_ubicacion():
    condicion = {"tipo_evento": "EVENTO_CLIMATICO", "ubicacion": "BOG"}
    evento = _evento(tipo="EVENTO_CLIMATICO", vuelo=None, ubicacion="BOG")
    assert ServicioTelemetria._aplica(condicion, evento) is True


def test_aplica_clima_que_no_coincide_es_falso():
    condicion = {"tipo_evento": "EVENTO_CLIMATICO", "ubicacion": "MED"}
    evento = _evento(tipo="EVENTO_CLIMATICO", vuelo=None, ubicacion="BOG")
    assert ServicioTelemetria._aplica(condicion, evento) is False


def test_aplica_tipo_desconocido_es_falso():
    condicion = {"tipo_evento": "TERREMOTO"}
    assert ServicioTelemetria._aplica(condicion, _evento(tipo="TERREMOTO")) is False


# --- procesar: caminos del servicio ------------------------------------------------------


def _poliza_parametrica(descripcion, estado=EstadoRegistroPoliza.VIGENTE, **cambios):
    datos = {
        "poliza_id": "POL-PM",
        "numero_poliza": "SOL-PM-0001",
        "cliente_id": "CLI-001",
        "ramo": RamoPoliza.PARAMETRICO,
        "estado": estado,
        "titular_nombre": "Ana Pérez",
        "titular_tipo_documento": "CC",
        "titular_numero_documento": "1012345678",
        "fecha_inicio": date(2026, 10, 6),
        "fecha_fin": date(2026, 11, 5),
        "prima_total": Decimal("45000.00"),
        "cobertura_principal": CoberturaPoliza(
            codigo="RETRASO_DE_VUELO",
            nombre="Retraso de vuelo",
            suma_asegurada=Decimal("500000.00"),
            descripcion=descripcion,
        ),
        "codigo_verificacion": "a1b2c3d4e5f60718",
        "emitida_en": datetime(2026, 10, 1, tzinfo=UTC),
    }
    if estado is EstadoRegistroPoliza.CANCELADA:
        datos["cancelada_en"] = datetime(2026, 10, 2, tzinfo=UTC)
    datos.update(cambios)
    return Poliza(**datos)


def _servicio(*polizas):
    repo_polizas = RepositorioPolizasEnMemoria()
    for p in polizas:
        repo_polizas.guardar(p)
    return ServicioTelemetria(
        RepositorioSiniestrosEnMemoria(),
        repo_polizas,
        reloj=lambda: AHORA,
    )


def test_umbral_ausente_no_crea_siniestro():
    # La condición casa el vuelo pero no define umbral_disparo: no se puede comparar.
    servicio = _servicio(
        _poliza_parametrica("tipo_evento=RETRASO_VUELO; numero_vuelo=AV123; ubicacion=BOG")
    )
    r = servicio.procesar(_evento(valor="500"))
    assert r.resultado is ResultadoTelemetria.SIN_COBERTURA


def test_poliza_cancelada_no_aplica():
    servicio = _servicio(
        _poliza_parametrica(
            "tipo_evento=RETRASO_VUELO; numero_vuelo=AV123; umbral_disparo=180",
            estado=EstadoRegistroPoliza.CANCELADA,
        )
    )
    r = servicio.procesar(_evento(valor="215"))
    assert r.resultado is ResultadoTelemetria.SIN_COBERTURA


def test_clima_sobre_umbral_crea_siniestro():
    servicio = _servicio(
        _poliza_parametrica(
            "tipo_evento=EVENTO_CLIMATICO; ubicacion=BOG; umbral_disparo=80; unidad=MM"
        )
    )
    evento = EventoParametrico(
        evento_id="W-1",
        tipo_evento="EVENTO_CLIMATICO",
        valor_observado=Decimal("92.4"),
        fecha_evento=AHORA,
        ubicacion="BOG",
    )
    r = servicio.procesar(evento)
    assert r.resultado is ResultadoTelemetria.SINIESTRO_CREADO
    assert r.poliza_id == "POL-PM"


def test_crear_siniestro_sin_ubicacion_ni_vuelo_usa_lugar_por_defecto():
    servicio = _servicio(
        _poliza_parametrica("tipo_evento=EVENTO_CLIMATICO; ubicacion=BOG; umbral_disparo=10")
    )
    evento = EventoParametrico(
        evento_id="W-2",
        tipo_evento="EVENTO_CLIMATICO",
        valor_observado=Decimal("50"),
        fecha_evento=AHORA,
        ubicacion="BOG",
    )
    r = servicio.procesar(evento)
    creado = servicio._siniestros.obtener(r.siniestro_id)
    # El lugar sale de la ubicación del evento.
    assert creado.lugar == "BOG"
    assert creado.registrado_por == "TELEMETRIA"
