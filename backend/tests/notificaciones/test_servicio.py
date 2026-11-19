"""Registro de eventos como notificaciones: bandeja, idempotencia, push y agrupación."""

from datetime import timedelta

import pytest

from app.notificaciones.modelos import MotivoSinPush, TipoNotificacion, grupo_de, resumen_de
from tests.notificaciones.fabrica import (
    AHORA,
    CLIENTE,
    HOY,
    OTRO,
    crear_servicio,
    dispositivo,
    preferencia,
    repositorios_en_memoria,
    repositorios_sqlite,
)

SINIESTRO = TipoNotificacion.ESTADO_SINIESTRO


@pytest.fixture(params=["memoria", "sqlite"])
def entorno(request):
    if request.param == "memoria":
        yield crear_servicio(repositorios_en_memoria())
    else:
        repositorios, cerrar = repositorios_sqlite()
        yield crear_servicio(repositorios)
        cerrar()


def registrar(servicio, numero: int = 1, cliente_id: str = CLIENTE, tipo=SINIESTRO):
    return servicio.registrar(
        cliente_id,
        tipo,
        clave=f"SIN-{numero}:APROBADO",
        titulo="Tu siniestro cambió de estado",
        cuerpo=f"Tu siniestro SIN-{numero} fue aprobado.",
        datos={"siniestro_id": f"SIN-{numero}", "poliza_id": "POL-1"},
    )


# --- Bandeja: siempre se registra ----------------------------------------------------------


def test_el_evento_queda_registrado_en_la_bandeja_aunque_no_haya_push(entorno) -> None:
    servicio, repos, _ = entorno

    resultado = registrar(servicio)

    assert resultado.nueva is True
    assert resultado.push is None and resultado.motivo_sin_push is MotivoSinPush.SIN_DISPOSITIVOS
    guardada = repos.notificaciones.listar(CLIENTE)
    assert [n.notificacion_id for n in guardada] == [resultado.notificacion.notificacion_id]
    assert guardada[0].dia == HOY and guardada[0].creada_en == AHORA
    assert guardada[0].datos == {"siniestro_id": "SIN-1", "poliza_id": "POL-1"}
    assert repos.notificaciones.contar_no_leidas(CLIENTE) == 1


def test_con_el_push_deshabilitado_el_evento_igual_queda_en_la_bandeja(entorno) -> None:
    servicio, repos, _ = entorno
    repos.dispositivos.guardar(dispositivo("token-1"))
    repos.preferencias.guardar(preferencia(False))

    resultado = registrar(servicio)

    assert resultado.push is None
    assert resultado.motivo_sin_push is MotivoSinPush.PUSH_DESHABILITADO
    assert len(repos.notificaciones.listar(CLIENTE)) == 1


def test_con_el_push_deshabilitado_se_siguen_registrando_varios_eventos(entorno) -> None:
    servicio, repos, _ = entorno
    repos.dispositivos.guardar(dispositivo("token-1"))
    repos.preferencias.guardar(preferencia(False))

    for numero in (1, 2, 3):
        registrar(servicio, numero)

    assert len(repos.notificaciones.listar(CLIENTE)) == 3
    assert repos.notificaciones.contar_no_leidas(CLIENTE) == 3


# --- Idempotencia --------------------------------------------------------------------------


def test_registrar_el_mismo_evento_dos_veces_no_duplica_ni_vuelve_a_notificar(entorno) -> None:
    servicio, repos, _ = entorno
    repos.dispositivos.guardar(dispositivo("token-1"))
    primero = registrar(servicio, 1)

    repetido = registrar(servicio, 1)

    assert repetido.nueva is False and repetido.push is None
    assert repetido.notificacion == primero.notificacion
    assert len(repos.notificaciones.listar(CLIENTE)) == 1


# --- Push ----------------------------------------------------------------------------------


def test_el_primer_evento_del_dia_genera_un_push_individual_con_su_destino(entorno) -> None:
    servicio, repos, _ = entorno
    repos.dispositivos.guardar(dispositivo("token-1", numero=1))
    repos.dispositivos.guardar(dispositivo("token-2", numero=2))

    resultado = registrar(servicio, 1)

    push = resultado.push
    assert resultado.motivo_sin_push is None
    assert push.cliente_id == CLIENTE
    assert sorted(push.tokens) == ["token-1", "token-2"]
    assert push.titulo == "Tu siniestro cambió de estado"
    assert push.cuerpo == "Tu siniestro SIN-1 fue aprobado."
    assert push.agrupado is False and push.total_del_grupo == 1
    assert push.etiqueta == grupo_de(SINIESTRO, HOY)
    assert push.datos == {
        "tipo": "ESTADO_SINIESTRO",
        "notificacion_id": resultado.notificacion.notificacion_id,
        "siniestro_id": "SIN-1",
        "poliza_id": "POL-1",
    }


def test_sin_preferencia_guardada_el_push_esta_habilitado(entorno) -> None:
    servicio, repos, _ = entorno
    repos.dispositivos.guardar(dispositivo("token-1"))

    assert registrar(servicio).push is not None


def test_un_dispositivo_dado_de_baja_no_recibe_push(entorno) -> None:
    servicio, repos, _ = entorno
    repos.dispositivos.guardar(dispositivo("token-1"))
    repos.dispositivos.desactivar(CLIENTE, "token-1", AHORA)

    resultado = registrar(servicio)

    assert resultado.push is None and resultado.motivo_sin_push is MotivoSinPush.SIN_DISPOSITIVOS


def test_el_push_es_solo_para_los_dispositivos_del_cliente(entorno) -> None:
    servicio, repos, _ = entorno
    repos.dispositivos.guardar(dispositivo("token-ajeno", cliente_id=OTRO))

    assert registrar(servicio, cliente_id=CLIENTE).push is None


# --- Agrupación ----------------------------------------------------------------------------


def test_los_eventos_del_mismo_tipo_el_mismo_dia_se_agrupan_en_un_resumen(entorno) -> None:
    servicio, repos, _ = entorno
    repos.dispositivos.guardar(dispositivo("token-1"))

    primero = registrar(servicio, 1).push
    segundo = registrar(servicio, 2).push
    tercero = registrar(servicio, 3).push

    assert primero.agrupado is False
    assert (segundo.agrupado, segundo.total_del_grupo) == (True, 2)
    assert (tercero.agrupado, tercero.total_del_grupo) == (True, 3)
    # Misma etiqueta: cada resumen reemplaza al anterior en el teléfono.
    assert primero.etiqueta == segundo.etiqueta == tercero.etiqueta
    assert tercero.titulo == "Cambios en tus siniestros"
    assert tercero.cuerpo == "Tienes 3 actualizaciones en tus siniestros hoy."
    # El resumen no lleva el destino de un solo evento: el cliente ve todos en la bandeja.
    assert "siniestro_id" not in tercero.datos
    assert tercero.datos["tipo"] == "ESTADO_SINIESTRO"
    assert len(repos.notificaciones.listar(CLIENTE)) == 3  # cada evento queda por separado


def test_otro_tipo_de_evento_no_se_agrupa_con_el_anterior(entorno) -> None:
    servicio, repos, _ = entorno
    repos.dispositivos.guardar(dispositivo("token-1"))
    registrar(servicio, 1, tipo=SINIESTRO)

    pago = registrar(servicio, 2, tipo=TipoNotificacion.PAGO_PARAMETRICO).push

    assert pago.agrupado is False and pago.total_del_grupo == 1
    assert pago.etiqueta == grupo_de(TipoNotificacion.PAGO_PARAMETRICO, HOY)


def test_al_dia_siguiente_vuelve_a_ser_un_push_individual(entorno) -> None:
    servicio, repos, reloj = entorno
    repos.dispositivos.guardar(dispositivo("token-1"))
    registrar(servicio, 1)
    registrar(servicio, 2)

    reloj.avanzar(days=1)
    nuevo = registrar(servicio, 3).push

    assert nuevo.agrupado is False
    assert nuevo.etiqueta == grupo_de(SINIESTRO, HOY + timedelta(days=1))


def test_el_dia_se_mide_en_hora_de_bogota_no_en_utc(entorno) -> None:
    servicio, repos, reloj = entorno
    repos.dispositivos.guardar(dispositivo("token-1"))
    reloj.ahora = AHORA.replace(hour=4, minute=0)  # 23:00 del 9 de diciembre en Bogotá
    antes_de_medianoche = registrar(servicio, 1).notificacion

    reloj.ahora = AHORA.replace(hour=6, minute=0)  # 01:00 del 10 de diciembre en Bogotá
    despues = registrar(servicio, 2).push

    assert antes_de_medianoche.dia == HOY - timedelta(days=1)
    assert despues.agrupado is False and despues.etiqueta == grupo_de(SINIESTRO, HOY)


def test_cada_cliente_tiene_su_propio_grupo(entorno) -> None:
    servicio, repos, _ = entorno
    repos.dispositivos.guardar(dispositivo("token-1", cliente_id=CLIENTE))
    repos.dispositivos.guardar(dispositivo("token-2", cliente_id=OTRO, numero=2))
    registrar(servicio, 1, cliente_id=CLIENTE)
    registrar(servicio, 2, cliente_id=CLIENTE)

    del_otro = registrar(servicio, 3, cliente_id=OTRO).push

    assert del_otro.agrupado is False and del_otro.tokens == ("token-2",)


def test_los_eventos_con_push_deshabilitado_tambien_cuentan_para_el_grupo(entorno) -> None:
    servicio, repos, _ = entorno
    repos.dispositivos.guardar(dispositivo("token-1"))
    repos.preferencias.guardar(preferencia(False))
    registrar(servicio, 1)
    registrar(servicio, 2)

    repos.preferencias.guardar(preferencia(True))
    reactivado = registrar(servicio, 3).push

    assert reactivado.total_del_grupo == 3 and reactivado.agrupado is True


# --- Carrera -------------------------------------------------------------------------------


def test_si_otra_solicitud_registro_el_evento_primero_se_devuelve_esa() -> None:
    servicio, repos, _ = crear_servicio()
    original = registrar(servicio, 1).notificacion
    notificaciones = repos.notificaciones

    class ConCarrera:
        """La consulta inicial no la ve, pero la inserción choca con la ya existente."""

        def __init__(self):
            self.consultas = 0

        def por_clave(self, cliente_id, clave):
            self.consultas += 1
            return None if self.consultas == 1 else notificaciones.por_clave(cliente_id, clave)

        def __getattr__(self, nombre):
            return getattr(notificaciones, nombre)

    servicio._notificaciones = ConCarrera()

    resultado = registrar(servicio, 1)

    assert resultado.nueva is False and resultado.notificacion == original


# --- Mensajes ------------------------------------------------------------------------------


@pytest.mark.parametrize("tipo", list(TipoNotificacion))
def test_cada_tipo_tiene_su_resumen_agrupado(tipo) -> None:
    titulo, cuerpo = resumen_de(tipo, 4)

    assert titulo and "4" in cuerpo
