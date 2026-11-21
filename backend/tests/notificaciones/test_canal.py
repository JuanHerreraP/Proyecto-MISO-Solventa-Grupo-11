"""Canal de envío: el adaptador simulado y la selección por configuración."""

import json
import logging

import pytest

from app.notificaciones.canal import (
    ConfiguracionPushInvalida,
    EnviadorPushSimulado,
    ResultadoEnvio,
    crear_enviador_push,
    enmascarar,
)
from app.notificaciones.fcm import EnviadorPushFCM
from app.notificaciones.modelos import PushPendiente


def push(*tokens: str, agrupado: bool = False) -> PushPendiente:
    return PushPendiente(
        cliente_id="CLI-001",
        tokens=tokens,
        titulo="Tu siniestro cambió de estado",
        cuerpo="Tu siniestro SIN-1 fue aprobado.",
        datos={"siniestro_id": "SIN-1"},
        etiqueta="ESTADO_SINIESTRO:2026-12-10",
        total_del_grupo=2 if agrupado else 1,
    )


# --- Simulado ------------------------------------------------------------------------------


def test_el_simulado_registra_el_envio_y_lo_deja_en_el_log(caplog) -> None:
    enviador = EnviadorPushSimulado()
    mensaje = push("token-abcdefghij")

    with caplog.at_level(logging.WARNING):
        resultado = enviador.enviar(mensaje)

    assert resultado == ResultadoEnvio(enviados=("token-abcdefghij",))
    assert enviador.enviados == [mensaje]
    assert "[PUSH SIMULADO]" in caplog.text
    assert "Tu siniestro cambió de estado" in caplog.text
    # El token es una credencial del dispositivo: en el log solo se ve el final.
    assert "…efghij" in caplog.text and "token-abcdefghij" not in caplog.text


def test_el_simulado_marca_los_pushes_agrupados_en_el_log(caplog) -> None:
    with caplog.at_level(logging.WARNING):
        EnviadorPushSimulado().enviar(push("token-1", agrupado=True))

    assert "[agrupado]" in caplog.text


def test_el_simulado_separa_los_tokens_segun_su_prefijo() -> None:
    enviador = EnviadorPushSimulado()

    resultado = enviador.enviar(push("token-ok", "tok_invalido_1", "tok_caido_1"))

    assert resultado.enviados == ("token-ok",)
    assert resultado.tokens_invalidos == ("tok_invalido_1",)
    assert resultado.fallidos == ("tok_caido_1",)


def test_si_ningun_token_se_envia_el_simulado_no_registra_nada(caplog) -> None:
    enviador = EnviadorPushSimulado()

    with caplog.at_level(logging.WARNING):
        resultado = enviador.enviar(push("tok_invalido_1"))

    assert resultado.enviados == () and enviador.enviados == []
    assert "[PUSH SIMULADO]" not in caplog.text


def test_enmascarar_solo_deja_el_final_del_token() -> None:
    assert enmascarar("abcdefghijkl") == "…ghijkl"
    assert enmascarar("abc") == "…"


# --- Selección por configuración -----------------------------------------------------------

CREDENCIALES = json.dumps(
    {
        "project_id": "solventa-test",
        "client_email": "push@solventa-test.iam.gserviceaccount.com",
        "private_key": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n",
    }
)


@pytest.fixture(autouse=True)
def limpiar_entorno(monkeypatch):
    for variable in ("PUSH_PROVEEDOR", "FCM_CREDENCIALES_JSON", "FCM_CREDENCIALES_PATH"):
        monkeypatch.delenv(variable, raising=False)


def test_por_defecto_el_canal_es_el_simulado() -> None:
    assert isinstance(crear_enviador_push(), EnviadorPushSimulado)


def test_sin_proveedor_pero_con_credencial_en_archivo_usa_fcm(monkeypatch, tmp_path) -> None:
    archivo = tmp_path / "fcm.json"
    archivo.write_text(CREDENCIALES, encoding="utf-8")
    monkeypatch.setenv("FCM_CREDENCIALES_PATH", str(archivo))

    assert isinstance(crear_enviador_push(), EnviadorPushFCM)


def test_sin_proveedor_pero_con_credencial_en_contenido_usa_fcm(monkeypatch) -> None:
    monkeypatch.setenv("FCM_CREDENCIALES_JSON", CREDENCIALES)

    assert isinstance(crear_enviador_push(), EnviadorPushFCM)


def test_el_proveedor_vacio_cuenta_como_no_indicado(monkeypatch) -> None:
    monkeypatch.setenv("PUSH_PROVEEDOR", "  ")
    monkeypatch.setenv("FCM_CREDENCIALES_JSON", CREDENCIALES)

    assert isinstance(crear_enviador_push(), EnviadorPushFCM)


def test_pedir_el_simulado_gana_sobre_la_credencial(monkeypatch) -> None:
    monkeypatch.setenv("PUSH_PROVEEDOR", "simulado")
    monkeypatch.setenv("FCM_CREDENCIALES_JSON", CREDENCIALES)

    assert isinstance(crear_enviador_push(), EnviadorPushSimulado)


def test_sin_proveedor_y_con_credencial_invalida_falla_en_vez_de_degradar(monkeypatch) -> None:
    monkeypatch.setenv("FCM_CREDENCIALES_JSON", "no es json")

    with pytest.raises(ConfiguracionPushInvalida):
        crear_enviador_push()


def test_se_puede_pedir_el_simulado_explicitamente(monkeypatch) -> None:
    monkeypatch.setenv("PUSH_PROVEEDOR", " Simulado ")

    assert isinstance(crear_enviador_push(), EnviadorPushSimulado)


def test_con_fcm_lee_la_credencial_del_contenido(monkeypatch) -> None:
    monkeypatch.setenv("PUSH_PROVEEDOR", "fcm")
    monkeypatch.setenv("FCM_CREDENCIALES_JSON", CREDENCIALES)

    assert isinstance(crear_enviador_push(), EnviadorPushFCM)


def test_con_fcm_lee_la_credencial_de_un_archivo(monkeypatch, tmp_path) -> None:
    archivo = tmp_path / "fcm.json"
    archivo.write_text(CREDENCIALES, encoding="utf-8")
    monkeypatch.setenv("PUSH_PROVEEDOR", "fcm")
    monkeypatch.setenv("FCM_CREDENCIALES_PATH", str(archivo))

    assert isinstance(crear_enviador_push(), EnviadorPushFCM)


def test_con_fcm_sin_credencial_falla_con_un_mensaje_claro(monkeypatch) -> None:
    monkeypatch.setenv("PUSH_PROVEEDOR", "fcm")

    with pytest.raises(ConfiguracionPushInvalida, match="FCM_CREDENCIALES"):
        crear_enviador_push()


def test_un_proveedor_desconocido_falla(monkeypatch) -> None:
    monkeypatch.setenv("PUSH_PROVEEDOR", "apns")

    with pytest.raises(ConfiguracionPushInvalida, match="apns"):
        crear_enviador_push()
