from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.cotizaciones.dominio.modelos import (
    CoberturaPrincipal,
    Cotizacion,
    EstadoCotizacion,
    RamoSeguro,
)


def cotizacion_valida(**cambios: object) -> Cotizacion:
    creada_en = datetime(2026, 10, 20, 12, tzinfo=UTC)
    datos = {
        "cotizacion_id": "COT-001",
        "cliente_id": "CLIENTE-001",
        "ramo": RamoSeguro.VIDA,
        "datos_riesgo": {"valor_asegurado": 200_000_000},
        "estado": EstadoCotizacion.VIGENTE,
        "prima_total": Decimal("125000.00"),
        "cobertura_principal": {
            "codigo": "VIDA-HIPOTECARIA",
            "nombre": "Vida hipotecaria",
            "suma_asegurada": Decimal("200000000.00"),
        },
        "creada_en": creada_en,
        "vigente_hasta": creada_en + timedelta(days=7),
    }
    datos.update(cambios)
    return Cotizacion.model_validate(datos)


def test_crea_borrador_sin_resultado_comercial() -> None:
    cotizacion = Cotizacion(
        cotizacion_id="COT-001",
        cliente_id="CLIENTE-001",
        ramo=RamoSeguro.VIAJE,
        creada_en=datetime.now(UTC),
    )

    assert cotizacion.estado is EstadoCotizacion.BORRADOR
    assert cotizacion.prima_total is None
    assert cotizacion.cobertura_principal is None


def test_crea_cotizacion_vigente_con_precio_y_cobertura() -> None:
    cotizacion = cotizacion_valida()

    assert cotizacion.prima_total == Decimal("125000.00")
    assert isinstance(cotizacion.cobertura_principal, CoberturaPrincipal)
    assert cotizacion.moneda == "COP"


@pytest.mark.parametrize(
    "campo_faltante",
    ["prima_total", "cobertura_principal", "vigente_hasta"],
)
def test_rechaza_cotizacion_procesada_sin_resultado_completo(
    campo_faltante: str,
) -> None:
    with pytest.raises(ValidationError, match="requiere prima, cobertura y fecha de vigencia"):
        cotizacion_valida(**{campo_faltante: None})


def test_rechaza_vigencia_anterior_a_la_creacion() -> None:
    creada_en = datetime(2026, 10, 20, 12, tzinfo=UTC)

    with pytest.raises(ValidationError, match="debe terminar después de la creación"):
        cotizacion_valida(creada_en=creada_en, vigente_hasta=creada_en)


def test_identifica_si_una_cotizacion_esta_vigente() -> None:
    cotizacion = cotizacion_valida()

    assert cotizacion.esta_vigente(cotizacion.creada_en + timedelta(days=1))
    assert not cotizacion.esta_vigente(cotizacion.vigente_hasta)
    assert cotizacion.estado_en(cotizacion.vigente_hasta) is EstadoCotizacion.EXPIRADA


def test_una_cotizacion_aceptada_ya_no_se_considera_vigente() -> None:
    cotizacion = cotizacion_valida(estado=EstadoCotizacion.ACEPTADA)

    assert not cotizacion.esta_vigente(cotizacion.creada_en + timedelta(days=1))
