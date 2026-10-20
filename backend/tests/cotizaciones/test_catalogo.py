import pytest
from pydantic import ValidationError

from app.cotizaciones.dominio.catalogo import (
    CampoRiesgo,
    DefinicionRamo,
    TipoCampo,
    consultar_catalogo_ramos,
    consultar_ramo,
)
from app.cotizaciones.dominio.modelos import RamoSeguro


def test_catalogo_expone_los_ramos_definidos_por_la_historia() -> None:
    catalogo = consultar_catalogo_ramos()

    assert {definicion.ramo for definicion in catalogo} == set(RamoSeguro)


@pytest.mark.parametrize("ramo", list(RamoSeguro))
def test_cada_ramo_define_campos_requeridos_sin_repetir(ramo: RamoSeguro) -> None:
    definicion = consultar_ramo(ramo)
    codigos = [campo.codigo for campo in definicion.campos]

    assert any(campo.requerido for campo in definicion.campos)
    assert len(codigos) == len(set(codigos))


def test_parametrico_admite_eventos_de_vuelo_y_clima() -> None:
    definicion = consultar_ramo(RamoSeguro.PARAMETRICO)
    tipo_evento = next(campo for campo in definicion.campos if campo.codigo == "tipo_evento")

    assert tipo_evento.tipo is TipoCampo.OPCION
    assert tipo_evento.opciones == ("RETRASO_VUELO", "EVENTO_CLIMATICO")
    assert {campo.codigo for campo in definicion.campos if not campo.requerido} == {
        "numero_vuelo",
        "ubicacion",
    }


def test_rechaza_un_campo_de_opcion_sin_valores_permitidos() -> None:
    with pytest.raises(ValidationError, match="debe declarar sus valores permitidos"):
        CampoRiesgo(
            codigo="tipo_evento",
            etiqueta="Tipo de evento",
            tipo=TipoCampo.OPCION,
            descripcion="Evento cubierto.",
        )


def test_rechaza_codigos_de_campo_repetidos_en_un_ramo() -> None:
    campo = CampoRiesgo(
        codigo="destino",
        etiqueta="Destino",
        tipo=TipoCampo.TEXTO,
        descripcion="Destino del viaje.",
    )

    with pytest.raises(ValidationError, match="no pueden repetir el código"):
        DefinicionRamo(
            ramo=RamoSeguro.VIAJE,
            nombre="Seguro de viaje",
            descripcion="Protección durante el viaje.",
            campos=(campo, campo),
        )
