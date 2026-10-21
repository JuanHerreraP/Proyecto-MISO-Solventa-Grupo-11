from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.cotizaciones.dominio.modelos import RamoSeguro
from app.cotizaciones.dominio.validacion import (
    CodigoErrorDato,
    DatosRiesgoInvalidosError,
    validar_datos_riesgo,
)


def datos_validos(ramo: RamoSeguro) -> dict[str, object]:
    casos = {
        RamoSeguro.VIAJE: {
            "destino": "Lima",
            "fecha_inicio": "2027-01-10",
            "fecha_fin": "2027-01-20",
            "numero_viajeros": 2,
            "valor_asegurado": "15000000.00",
        },
        RamoSeguro.PROTECCION_DISPOSITIVOS: {
            "tipo_dispositivo": "CELULAR",
            "marca": "Acme",
            "modelo": "X1",
            "valor_dispositivo": 3_500_000,
            "fecha_compra": "2026-01-10",
            "meses_cobertura": 12,
        },
        RamoSeguro.VIDA: {
            "fecha_nacimiento": "1990-05-20",
            "valor_asegurado": 100_000_000,
            "meses_cobertura": 12,
            "fumador": False,
        },
        RamoSeguro.PARAMETRICO: {
            "tipo_evento": "RETRASO_VUELO",
            "fecha_inicio": "2027-02-01",
            "fecha_fin": "2027-02-02",
            "umbral_disparo": 180,
            "valor_asegurado": 1_000_000,
            "numero_vuelo": "AV123",
        },
    }
    return casos[ramo]


@pytest.mark.parametrize("ramo", list(RamoSeguro))
def test_valida_y_normaliza_los_datos_de_cada_ramo(ramo: RamoSeguro) -> None:
    resultado = validar_datos_riesgo(ramo, datos_validos(ramo))

    assert resultado
    assert any(type(valor) is date for valor in resultado.values())
    assert any(isinstance(valor, Decimal) for valor in resultado.values())


def test_informa_todos_los_campos_obligatorios_faltantes() -> None:
    with pytest.raises(DatosRiesgoInvalidosError) as capturado:
        validar_datos_riesgo(RamoSeguro.VIAJE, {"destino": "Lima"})

    assert {error.campo for error in capturado.value.errores} == {
        "fecha_inicio",
        "fecha_fin",
        "numero_viajeros",
        "valor_asegurado",
    }
    assert all(error.codigo is CodigoErrorDato.REQUERIDO for error in capturado.value.errores)


def test_rechaza_campos_que_no_pertenecen_al_ramo() -> None:
    datos = datos_validos(RamoSeguro.VIAJE) | {"placa_vehiculo": "ABC123"}

    with pytest.raises(DatosRiesgoInvalidosError) as capturado:
        validar_datos_riesgo(RamoSeguro.VIAJE, datos)

    assert capturado.value.errores[0].campo == "placa_vehiculo"
    assert capturado.value.errores[0].codigo is CodigoErrorDato.CAMPO_NO_PERMITIDO


def test_rechaza_tipos_y_valores_invalidos() -> None:
    datos = datos_validos(RamoSeguro.VIAJE) | {
        "destino": " ",
        "numero_viajeros": "dos",
    }

    with pytest.raises(DatosRiesgoInvalidosError) as capturado:
        validar_datos_riesgo(RamoSeguro.VIAJE, datos)

    errores = {error.campo: error.codigo for error in capturado.value.errores}
    assert errores == {
        "destino": CodigoErrorDato.VALOR_INVALIDO,
        "numero_viajeros": CodigoErrorDato.TIPO_INVALIDO,
    }


def test_rechaza_periodos_invertidos_y_valores_no_positivos() -> None:
    datos = datos_validos(RamoSeguro.VIAJE) | {
        "fecha_fin": "2027-01-09",
        "numero_viajeros": 0,
        "valor_asegurado": -1,
    }

    with pytest.raises(DatosRiesgoInvalidosError) as capturado:
        validar_datos_riesgo(RamoSeguro.VIAJE, datos)

    assert {error.campo for error in capturado.value.errores} == {
        "fecha_fin",
        "numero_viajeros",
        "valor_asegurado",
    }


@pytest.mark.parametrize(
    ("tipo_evento", "campo_requerido"),
    [
        ("RETRASO_VUELO", "numero_vuelo"),
        ("EVENTO_CLIMATICO", "ubicacion"),
    ],
)
def test_parametrico_exige_el_dato_del_evento_seleccionado(
    tipo_evento: str,
    campo_requerido: str,
) -> None:
    datos = datos_validos(RamoSeguro.PARAMETRICO)
    datos["tipo_evento"] = tipo_evento
    datos.pop("numero_vuelo")

    with pytest.raises(DatosRiesgoInvalidosError) as capturado:
        validar_datos_riesgo(RamoSeguro.PARAMETRICO, datos)

    assert any(
        error.campo == campo_requerido and error.codigo is CodigoErrorDato.REQUERIDO
        for error in capturado.value.errores
    )


def test_rechaza_fecha_de_compra_futura() -> None:
    datos = datos_validos(RamoSeguro.PROTECCION_DISPOSITIVOS) | {
        "fecha_compra": (date.today() + timedelta(days=1)).isoformat()
    }

    with pytest.raises(DatosRiesgoInvalidosError) as capturado:
        validar_datos_riesgo(RamoSeguro.PROTECCION_DISPOSITIVOS, datos)

    assert capturado.value.errores[0].campo == "fecha_compra"
    assert capturado.value.errores[0].codigo is CodigoErrorDato.VALOR_INVALIDO
