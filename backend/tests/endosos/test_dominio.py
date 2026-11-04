"""Reglas del endoso: beneficiarios, coberturas opcionales y ajuste pro-rata (HU16)."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.polizas.dominio.endosos import (
    CoberturaSolicitada,
    CodigoModificacion,
    ModificacionInvalida,
    PolizaNoModificable,
    SolicitudModificacion,
    TipoCambio,
    TipoEndoso,
    coberturas_disponibles,
    proponer_endoso,
)
from app.polizas.dominio.modelos import (
    CoberturaPoliza,
    EstadoPoliza,
    EstadoRegistroPoliza,
    RamoPoliza,
)
from tests.endosos.fabrica import HOY, beneficiario, dos_beneficiarios, poliza, solo_coberturas


def codigo_de(error: pytest.ExceptionInfo[ModificacionInvalida]) -> CodigoModificacion:
    return error.value.codigo


# --- Beneficiarios -----------------------------------------------------------------------


def test_designar_beneficiarios_que_suman_100_no_cambia_la_prima() -> None:
    propuesta = proponer_endoso(
        poliza(), SolicitudModificacion(beneficiarios=dos_beneficiarios()), HOY
    )

    assert propuesta.tipo is TipoEndoso.BENEFICIARIOS
    assert [c.tipo for c in propuesta.cambios] == [TipoCambio.BENEFICIARIO_AGREGADO] * 2
    assert propuesta.ajuste_prima == Decimal("0.00")
    assert propuesta.prima_nueva == Decimal("150000.00")


@pytest.mark.parametrize("porcentajes", [("60", "30"), ("60", "50"), ("99.99", "0.02")])
def test_los_porcentajes_deben_sumar_exactamente_100(porcentajes) -> None:
    beneficiarios = [
        beneficiario(porcentaje=porcentajes[0]),
        beneficiario("Sofía Gómez", "1098765433", porcentajes[1]),
    ]

    with pytest.raises(ModificacionInvalida) as error:
        proponer_endoso(poliza(), SolicitudModificacion(beneficiarios=beneficiarios), HOY)

    assert codigo_de(error) is CodigoModificacion.PORCENTAJES_NO_SUMAN_100


def test_porcentajes_con_decimales_que_suman_100_son_validos() -> None:
    beneficiarios = [
        beneficiario(porcentaje="33.34"),
        beneficiario("Sofía Gómez", "1098765433", "33.33"),
        beneficiario("Tomás Gómez", "1098765434", "33.33"),
    ]

    propuesta = proponer_endoso(poliza(), SolicitudModificacion(beneficiarios=beneficiarios), HOY)

    assert len(propuesta.beneficiarios) == 3


def test_quitar_todos_los_beneficiarios_deja_a_los_herederos_legales() -> None:
    con_beneficiarios = poliza(beneficiarios=dos_beneficiarios())

    propuesta = proponer_endoso(con_beneficiarios, SolicitudModificacion(beneficiarios=[]), HOY)

    assert propuesta.beneficiarios == []
    assert [c.tipo for c in propuesta.cambios] == [TipoCambio.BENEFICIARIO_RETIRADO] * 2


def test_editar_un_beneficiario_registra_el_antes_y_el_despues() -> None:
    con_beneficiarios = poliza(beneficiarios=dos_beneficiarios())
    editados = [
        beneficiario(porcentaje="50"),
        beneficiario("Sofía Gómez", "1098765433", "50", parentesco="Hija"),
    ]

    propuesta = proponer_endoso(
        con_beneficiarios, SolicitudModificacion(beneficiarios=editados), HOY
    )

    assert [c.tipo for c in propuesta.cambios] == [TipoCambio.BENEFICIARIO_MODIFICADO] * 2
    assert propuesta.cambios[0].antes["porcentaje"] == "60.00"
    assert propuesta.cambios[0].despues["porcentaje"] == "50.00"


def test_no_se_repite_un_beneficiario() -> None:
    repetidos = [beneficiario(porcentaje="50"), beneficiario(porcentaje="50")]

    with pytest.raises(ModificacionInvalida) as error:
        proponer_endoso(poliza(), SolicitudModificacion(beneficiarios=repetidos), HOY)

    assert codigo_de(error) is CodigoModificacion.BENEFICIARIO_DUPLICADO
    assert error.value.campo == "beneficiarios[1].numero_documento"


def test_el_asegurado_no_es_beneficiario_de_su_propia_vida() -> None:
    titular = [beneficiario(documento="1012345678", porcentaje="100")]

    with pytest.raises(ModificacionInvalida) as error:
        proponer_endoso(poliza(), SolicitudModificacion(beneficiarios=titular), HOY)

    assert codigo_de(error) is CodigoModificacion.BENEFICIARIO_ES_TITULAR


def test_solo_las_polizas_de_vida_tienen_beneficiarios() -> None:
    viaje = poliza(ramo=RamoPoliza.VIAJE)

    with pytest.raises(ModificacionInvalida) as error:
        proponer_endoso(
            viaje, SolicitudModificacion(beneficiarios=[beneficiario(porcentaje="100")]), HOY
        )

    assert codigo_de(error) is CodigoModificacion.BENEFICIARIOS_NO_APLICAN


def test_hay_un_maximo_de_beneficiarios() -> None:
    once = [beneficiario(f"Persona {i}", f"10000000{i:02d}", "9.09") for i in range(11)]

    with pytest.raises(ModificacionInvalida) as error:
        proponer_endoso(poliza(), SolicitudModificacion(beneficiarios=once), HOY)

    assert codigo_de(error) is CodigoModificacion.DEMASIADOS_BENEFICIARIOS


# --- Coberturas opcionales y prima -------------------------------------------------------


def test_incluir_una_cobertura_cobra_la_parte_que_falta_de_la_vigencia() -> None:
    propuesta = proponer_endoso(
        poliza(), solo_coberturas(INCAPACIDAD_TOTAL_PERMANENTE="50000000.00"), HOY
    )

    # 50.000.000 x 0,00012 x 365/30 = 73.000 por el año; quedan 183 de 365 días.
    assert propuesta.tipo is TipoEndoso.COBERTURAS
    assert propuesta.dias_vigencia == 365
    assert propuesta.dias_restantes == 183
    assert propuesta.fecha_efecto == HOY
    assert propuesta.prima_opcionales_nueva == Decimal("73000.00")
    assert propuesta.ajuste_prima == Decimal("36600.00")
    assert propuesta.prima_nueva == Decimal("186600.00")
    assert propuesta.cambios[0].tipo is TipoCambio.COBERTURA_INCLUIDA


def test_excluir_una_cobertura_devuelve_la_prima_no_devengada() -> None:
    con_itp = poliza(
        coberturas_opcionales=[
            CoberturaPoliza(
                codigo="INCAPACIDAD_TOTAL_PERMANENTE",
                nombre="Incapacidad total y permanente",
                suma_asegurada=Decimal("50000000.00"),
            )
        ],
        prima_total=Decimal("186600.00"),
    )

    propuesta = proponer_endoso(con_itp, SolicitudModificacion(coberturas_opcionales=[]), HOY)

    assert propuesta.ajuste_prima == Decimal("-36600.00")
    assert propuesta.prima_nueva == Decimal("150000.00")
    assert propuesta.cambios[0].tipo is TipoCambio.COBERTURA_EXCLUIDA


def test_aumentar_la_suma_cobra_solo_la_diferencia() -> None:
    con_itp = poliza(
        coberturas_opcionales=[
            CoberturaPoliza(
                codigo="INCAPACIDAD_TOTAL_PERMANENTE",
                nombre="Incapacidad total y permanente",
                suma_asegurada=Decimal("50000000.00"),
            )
        ]
    )

    propuesta = proponer_endoso(
        con_itp, solo_coberturas(INCAPACIDAD_TOTAL_PERMANENTE="100000000.00"), HOY
    )

    assert propuesta.cambios[0].tipo is TipoCambio.COBERTURA_MODIFICADA
    assert propuesta.ajuste_prima == Decimal("36600.00")


def test_si_la_poliza_no_ha_empezado_el_ajuste_es_por_toda_la_vigencia() -> None:
    viaje = poliza(
        ramo=RamoPoliza.VIAJE,
        fecha_inicio=date(2026, 8, 1),
        fecha_fin=date(2026, 8, 30),
    )

    propuesta = proponer_endoso(viaje, solo_coberturas(EQUIPAJE="2000000.00"), HOY)

    # 2.000.000 x 0,003 x 30/30 = 6.000.
    assert propuesta.fecha_efecto == date(2026, 8, 1)
    assert propuesta.dias_restantes == propuesta.dias_vigencia == 30
    assert propuesta.ajuste_prima == Decimal("6000.00")


def test_el_ultimo_dia_de_vigencia_cuenta_un_dia() -> None:
    propuesta = proponer_endoso(
        poliza(), solo_coberturas(AUXILIO_FUNERARIO="5000000.00"), date(2026, 12, 31)
    )

    # 5.000.000 x 0,0003 x 365/30 = 18.250 por el año; 1 de 365 días = 50.
    assert propuesta.dias_restantes == 1
    assert propuesta.ajuste_prima == Decimal("50.00")


def test_las_coberturas_salen_en_el_orden_del_catalogo() -> None:
    solicitud = solo_coberturas(
        AUXILIO_FUNERARIO="5000000.00", INCAPACIDAD_TOTAL_PERMANENTE="50000000.00"
    )

    propuesta = proponer_endoso(poliza(), solicitud, HOY)

    assert [c.codigo for c in propuesta.coberturas_opcionales] == [
        "INCAPACIDAD_TOTAL_PERMANENTE",
        "AUXILIO_FUNERARIO",
    ]


def test_una_cobertura_ajena_al_ramo_se_rechaza() -> None:
    with pytest.raises(ModificacionInvalida) as error:
        proponer_endoso(poliza(), solo_coberturas(EQUIPAJE="2000000.00"), HOY)

    assert codigo_de(error) is CodigoModificacion.COBERTURA_NO_DISPONIBLE
    assert error.value.campo == "coberturas_opcionales[0].codigo"


def test_el_parametrico_no_tiene_coberturas_opcionales() -> None:
    assert coberturas_disponibles(RamoPoliza.PARAMETRICO) == ()


def test_la_cobertura_no_se_repite() -> None:
    solicitud = SolicitudModificacion(
        coberturas_opcionales=[
            CoberturaSolicitada(codigo="AUXILIO_FUNERARIO", suma_asegurada=Decimal("2000000")),
            CoberturaSolicitada(codigo="AUXILIO_FUNERARIO", suma_asegurada=Decimal("3000000")),
        ]
    )

    with pytest.raises(ModificacionInvalida) as error:
        proponer_endoso(poliza(), solicitud, HOY)

    assert codigo_de(error) is CodigoModificacion.COBERTURA_DUPLICADA


@pytest.mark.parametrize(
    ("codigo", "suma"),
    [
        ("AUXILIO_FUNERARIO", "999999.99"),
        ("AUXILIO_FUNERARIO", "10000000.01"),
        # El amparo de incapacidad no puede superar la suma de la cobertura principal.
        ("INCAPACIDAD_TOTAL_PERMANENTE", "100000000.01"),
    ],
)
def test_la_suma_debe_estar_dentro_de_los_limites(codigo, suma) -> None:
    with pytest.raises(ModificacionInvalida) as error:
        proponer_endoso(poliza(), solo_coberturas(**{codigo: suma}), HOY)

    assert codigo_de(error) is CodigoModificacion.SUMA_FUERA_DE_RANGO


# --- Reglas generales --------------------------------------------------------------------


def test_beneficiarios_y_coberturas_en_un_solo_endoso() -> None:
    solicitud = SolicitudModificacion(
        beneficiarios=dos_beneficiarios(),
        coberturas_opcionales=solo_coberturas(AUXILIO_FUNERARIO="5000000.00").coberturas_opcionales,
    )

    propuesta = proponer_endoso(poliza(), solicitud, HOY)

    assert propuesta.tipo is TipoEndoso.BENEFICIARIOS_Y_COBERTURAS
    assert len(propuesta.cambios) == 3


def test_una_solicitud_que_no_cambia_nada_se_rechaza() -> None:
    con_beneficiarios = poliza(beneficiarios=dos_beneficiarios())

    for solicitud in (
        SolicitudModificacion(),
        SolicitudModificacion(beneficiarios=dos_beneficiarios()),
        SolicitudModificacion(coberturas_opcionales=[]),
    ):
        with pytest.raises(ModificacionInvalida) as error:
            proponer_endoso(con_beneficiarios, solicitud, HOY)
        assert codigo_de(error) is CodigoModificacion.SIN_CAMBIOS


@pytest.mark.parametrize(
    ("cambios", "estado"),
    [
        ({"fecha_fin": date(2026, 6, 30)}, EstadoPoliza.VENCIDA),
        (
            {
                "estado": EstadoRegistroPoliza.CANCELADA,
                "cancelada_en": datetime(2026, 6, 1, tzinfo=UTC),
            },
            EstadoPoliza.CANCELADA,
        ),
    ],
)
def test_una_poliza_vencida_o_cancelada_no_admite_endosos(cambios, estado) -> None:
    with pytest.raises(PolizaNoModificable) as error:
        proponer_endoso(poliza(**cambios), solo_coberturas(AUXILIO_FUNERARIO="5000000"), HOY)

    assert error.value.estado is estado
