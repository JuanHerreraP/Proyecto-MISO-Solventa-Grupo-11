"""`notificar`: registrar el evento y enviar el push sin que un fallo rompa el flujo."""

import logging

from app.notificaciones.canal import EnviadorPushSimulado, ResultadoEnvio
from app.notificaciones.modelos import TipoNotificacion
from tests.notificaciones.fabrica import (
    CLIENTE,
    crear_servicio,
    dispositivo,
    preferencia,
)

SINIESTRO = TipoNotificacion.ESTADO_SINIESTRO


def notificar(servicio, numero: int = 1):
    return servicio.notificar(
        CLIENTE,
        SINIESTRO,
        clave=f"SIN-{numero}:APROBADO",
        titulo="Tu siniestro cambió de estado",
        cuerpo=f"Tu siniestro SIN-{numero} fue aprobado.",
        datos={"siniestro_id": f"SIN-{numero}"},
    )


def test_notificar_registra_el_evento_y_envia_el_push() -> None:
    enviador = EnviadorPushSimulado()
    servicio, repos, _ = crear_servicio(enviador=enviador)
    repos.dispositivos.guardar(dispositivo("token-1"))

    resultado = notificar(servicio)

    assert resultado.nueva is True
    assert resultado.envio == ResultadoEnvio(enviados=("token-1",))
    assert enviador.enviados == [resultado.push]
    assert len(repos.notificaciones.listar(CLIENTE)) == 1


def test_sin_dispositivos_no_se_intenta_enviar() -> None:
    enviador = EnviadorPushSimulado()
    servicio, repos, _ = crear_servicio(enviador=enviador)

    resultado = notificar(servicio)

    assert resultado.envio is None and enviador.enviados == []
    assert len(repos.notificaciones.listar(CLIENTE)) == 1


def test_con_el_push_deshabilitado_no_se_envia_pero_queda_en_la_bandeja() -> None:
    enviador = EnviadorPushSimulado()
    servicio, repos, _ = crear_servicio(enviador=enviador)
    repos.dispositivos.guardar(dispositivo("token-1"))
    repos.preferencias.guardar(preferencia(False))

    resultado = notificar(servicio)

    assert resultado.envio is None and enviador.enviados == []
    assert len(repos.notificaciones.listar(CLIENTE)) == 1


def test_sin_canal_conectado_solo_se_registra() -> None:
    servicio, repos, _ = crear_servicio(enviador=None)
    repos.dispositivos.guardar(dispositivo("token-1"))

    resultado = notificar(servicio)

    assert resultado.push is not None and resultado.envio is None
    assert len(repos.notificaciones.listar(CLIENTE)) == 1


def test_un_token_invalido_se_da_de_baja_y_deja_de_recibir_push() -> None:
    servicio, repos, _ = crear_servicio(enviador=EnviadorPushSimulado())
    repos.dispositivos.guardar(dispositivo("tok_invalido_1", numero=1))
    repos.dispositivos.guardar(dispositivo("token-bueno", numero=2))

    resultado = notificar(servicio)

    assert resultado.envio.tokens_invalidos == ("tok_invalido_1",)
    assert [d.token for d in repos.dispositivos.activos_de(CLIENTE)] == ["token-bueno"]


def test_una_falla_pasajera_no_da_de_baja_el_token() -> None:
    servicio, repos, _ = crear_servicio(enviador=EnviadorPushSimulado())
    repos.dispositivos.guardar(dispositivo("tok_caido_1"))

    resultado = notificar(servicio)

    assert resultado.envio.fallidos == ("tok_caido_1",)
    assert len(repos.dispositivos.activos_de(CLIENTE)) == 1


def test_si_el_canal_lanza_el_evento_igual_queda_registrado_y_no_se_propaga(caplog) -> None:
    class Caido:
        def enviar(self, push):
            raise RuntimeError("FCM no responde")

    servicio, repos, _ = crear_servicio(enviador=Caido())
    repos.dispositivos.guardar(dispositivo("token-1"))

    with caplog.at_level(logging.ERROR):
        resultado = notificar(servicio)

    assert resultado.nueva is True and resultado.envio is None
    assert len(repos.notificaciones.listar(CLIENTE)) == 1
    assert "No se pudo enviar el push" in caplog.text
    assert len(repos.dispositivos.activos_de(CLIENTE)) == 1


def test_notificar_el_mismo_evento_dos_veces_envia_una_sola_vez() -> None:
    enviador = EnviadorPushSimulado()
    servicio, repos, _ = crear_servicio(enviador=enviador)
    repos.dispositivos.guardar(dispositivo("token-1"))

    notificar(servicio, 1)
    repetido = notificar(servicio, 1)

    assert repetido.nueva is False and repetido.envio is None
    assert len(enviador.enviados) == 1


def test_los_eventos_del_mismo_dia_envian_un_resumen_que_reemplaza_al_anterior() -> None:
    enviador = EnviadorPushSimulado()
    servicio, repos, _ = crear_servicio(enviador=enviador)
    repos.dispositivos.guardar(dispositivo("token-1"))

    notificar(servicio, 1)
    notificar(servicio, 2)

    primero, segundo = enviador.enviados
    assert primero.agrupado is False and segundo.agrupado is True
    assert primero.etiqueta == segundo.etiqueta
    assert segundo.cuerpo == "Tienes 2 actualizaciones en tus siniestros hoy."
