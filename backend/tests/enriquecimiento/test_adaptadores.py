import asyncio

import httpx
import pytest

from app.perfilamiento.dominio.modelos import NivelRiesgoZona
from app.perfilamiento.enriquecimiento.adaptadores import (
    AdaptadorOpenData,
    AdaptadorOpenFinance,
    FuenteSimuladaOpenData,
    FuenteSimuladaOpenFinance,
    clasificar_zona,
)
from app.perfilamiento.enriquecimiento.cliente_http import ConfiguracionInsegura, crear_cliente
from app.perfilamiento.enriquecimiento.configuracion import crear_fuentes
from app.perfilamiento.enriquecimiento.puertos import FuenteNoDisponible

OPEN_FINANCE_OK = {
    "customer_id": "CLI-001",
    "payment_history": {"on_time_payments": 45, "total_payments": 50},
    "monthly_income": 5_000_000,
    "monthly_debt_payments": 1_500_000,
}
OPEN_DATA_OK = {
    "documento": "CLI-001",
    "antiguedad_laboral_meses": 36,
    "antiguedad_residencia_meses": 24,
    "zona_inmueble": {"indice_riesgo": 40},
}


def cliente(manejador) -> httpx.AsyncClient:
    return crear_cliente(
        "https://proveedor.example", "token-de-prueba", transporte=httpx.MockTransport(manejador)
    )


def responde(cuerpo, codigo: int = 200):
    return lambda solicitud: httpx.Response(codigo, json=cuerpo)


def consultar(adaptador):
    return asyncio.run(adaptador.consultar("CLI-001"))


def test_open_finance_traduce_el_contrato_del_proveedor_al_modelo_interno():
    senales = consultar(AdaptadorOpenFinance(cliente(responde(OPEN_FINANCE_OK))))

    assert senales.comportamiento_pago == pytest.approx(0.9)
    assert senales.nivel_endeudamiento == pytest.approx(0.3)


def test_open_finance_acota_el_endeudamiento_al_cien_por_ciento():
    cuerpo = {**OPEN_FINANCE_OK, "monthly_debt_payments": 9_000_000}

    assert consultar(AdaptadorOpenFinance(cliente(responde(cuerpo)))).nivel_endeudamiento == 1.0


def test_open_data_traduce_el_contrato_del_proveedor_al_modelo_interno():
    senales = consultar(AdaptadorOpenData(cliente(responde(OPEN_DATA_OK))))

    assert senales.estabilidad == pytest.approx(0.5)
    assert senales.riesgo_zona is NivelRiesgoZona.MEDIO


@pytest.mark.parametrize(
    ("indice", "esperado"),
    [
        (0, NivelRiesgoZona.BAJO),
        (33.9, NivelRiesgoZona.BAJO),
        (34, NivelRiesgoZona.MEDIO),
        (66.9, NivelRiesgoZona.MEDIO),
        (67, NivelRiesgoZona.ALTO),
        (100, NivelRiesgoZona.ALTO),
    ],
)
def test_limites_del_riesgo_de_zona(indice, esperado):
    assert clasificar_zona(indice) is esperado


def test_cada_solicitud_va_autenticada_y_a_la_ruta_del_cliente():
    vistas = []

    def manejador(solicitud: httpx.Request) -> httpx.Response:
        vistas.append(solicitud)
        return httpx.Response(200, json=OPEN_FINANCE_OK)

    consultar(AdaptadorOpenFinance(cliente(manejador)))

    assert vistas[0].headers["Authorization"] == "Bearer token-de-prueba"
    assert vistas[0].url.scheme == "https"
    assert vistas[0].url.path == "/v1/customers/CLI-001"


@pytest.mark.parametrize("codigo", [401, 404, 429, 500, 503])
def test_respuesta_de_error_del_proveedor_es_fuente_no_disponible(codigo):
    with pytest.raises(FuenteNoDisponible, match=f"HTTP {codigo}"):
        consultar(AdaptadorOpenFinance(cliente(responde({"error": "x"}, codigo))))


def test_tiempo_agotado_es_fuente_no_disponible():
    def manejador(solicitud: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("lento", request=solicitud)

    with pytest.raises(FuenteNoDisponible, match="tiempo de espera agotado"):
        consultar(AdaptadorOpenData(cliente(manejador)))


def test_error_de_conexion_es_fuente_no_disponible():
    def manejador(solicitud: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin ruta", request=solicitud)

    with pytest.raises(FuenteNoDisponible, match="error de conexión"):
        consultar(AdaptadorOpenFinance(cliente(manejador)))


@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {**OPEN_FINANCE_OK, "monthly_income": 0},
        {**OPEN_FINANCE_OK, "payment_history": {"on_time_payments": 1, "total_payments": 0}},
        {**OPEN_FINANCE_OK, "monthly_debt_payments": "mucho"},
        ["no", "es", "un", "objeto"],
    ],
)
def test_respuesta_invalida_de_open_finance_es_fuente_no_disponible(cuerpo):
    with pytest.raises(FuenteNoDisponible):
        consultar(AdaptadorOpenFinance(cliente(responde(cuerpo))))


def test_respuesta_invalida_de_open_data_es_fuente_no_disponible():
    cuerpo = {**OPEN_DATA_OK, "zona_inmueble": {"indice_riesgo": 250}}

    with pytest.raises(FuenteNoDisponible, match="contenido inválido"):
        consultar(AdaptadorOpenData(cliente(responde(cuerpo))))


def test_respuesta_que_no_es_json_es_fuente_no_disponible():
    def manejador(solicitud: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>mantenimiento</html>")

    with pytest.raises(FuenteNoDisponible, match="no es JSON"):
        consultar(AdaptadorOpenData(cliente(manejador)))


def test_no_se_permite_http_sin_cifrar():
    with pytest.raises(ConfiguracionInsegura, match="https"):
        crear_cliente("http://proveedor.example", "token")


def test_http_solo_con_permiso_explicito_para_desarrollo():
    assert crear_cliente("http://localhost:9000", "token", permitir_http=True) is not None


def test_no_se_permite_una_integracion_sin_token():
    with pytest.raises(ConfiguracionInsegura, match="token"):
        crear_cliente("https://proveedor.example", "")


def test_los_simuladores_son_estables_por_cliente_y_distintos_entre_clientes():
    finanzas, datos = FuenteSimuladaOpenFinance(), FuenteSimuladaOpenData()

    assert consultar(finanzas) == consultar(finanzas)
    assert consultar(datos) == consultar(datos)
    assert asyncio.run(finanzas.consultar("CLI-A")) != asyncio.run(finanzas.consultar("CLI-B"))


def test_sin_url_configurada_se_usan_los_simuladores():
    fuentes = crear_fuentes({}, tiempo_limite=0.25)

    assert [f.proveedor for f in fuentes] == ["simulador-open-finance", "simulador-open-data"]


def test_con_url_configurada_se_usan_los_adaptadores_http():
    entorno = {
        "OPEN_FINANCE_URL": "https://of.example",
        "OPEN_FINANCE_TOKEN": "t1",
        "OPEN_DATA_URL": "https://od.example",
        "OPEN_DATA_TOKEN": "t2",
    }

    fuentes = crear_fuentes(entorno, tiempo_limite=0.25)

    assert [type(f) for f in fuentes] == [AdaptadorOpenFinance, AdaptadorOpenData]


def test_url_configurada_sin_token_no_arranca():
    with pytest.raises(ConfiguracionInsegura):
        crear_fuentes({"OPEN_FINANCE_URL": "https://of.example"}, tiempo_limite=0.25)
