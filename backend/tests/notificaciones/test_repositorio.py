"""Repositorios de notificaciones, dispositivos y preferencias: en memoria y sobre la base."""

from datetime import timedelta

import pytest

from app.notificaciones.modelos import TipoNotificacion
from tests.notificaciones.fabrica import (
    AHORA,
    CLIENTE,
    HOY,
    OTRO,
    dispositivo,
    notificacion,
    preferencia,
    repositorios_en_memoria,
    repositorios_sqlite,
)


@pytest.fixture(params=["memoria", "sqlite"])
def repos(request):
    if request.param == "memoria":
        yield repositorios_en_memoria()
    else:
        repositorios, cerrar = repositorios_sqlite()
        yield repositorios
        cerrar()


# --- Notificaciones ------------------------------------------------------------------------


def test_crear_y_leer_una_notificacion_conserva_todos_los_campos(repos) -> None:
    original = notificacion(1)

    assert repos.notificaciones.crear(original) is True

    assert repos.notificaciones.por_clave(CLIENTE, original.clave) == original
    assert repos.notificaciones.por_clave(CLIENTE, "otra") is None
    assert repos.notificaciones.por_clave(OTRO, original.clave) is None


def test_el_mismo_evento_no_se_registra_dos_veces_por_cliente(repos) -> None:
    repos.notificaciones.crear(notificacion(1, clave="SIN-1:APROBADO"))

    assert repos.notificaciones.crear(notificacion(2, clave="SIN-1:APROBADO")) is False
    # Otro cliente sí puede tener un evento con la misma clave.
    assert repos.notificaciones.crear(notificacion(3, cliente_id=OTRO, clave="SIN-1:APROBADO"))
    assert len(repos.notificaciones.listar(CLIENTE)) == 1


def test_la_sesion_sigue_usable_tras_un_evento_repetido(repos) -> None:
    repos.notificaciones.crear(notificacion(1, clave="K"))
    repos.notificaciones.crear(notificacion(2, clave="K"))

    assert repos.notificaciones.crear(notificacion(3, clave="K2")) is True


def test_lista_de_la_mas_reciente_a_la_mas_antigua_y_pagina(repos) -> None:
    for i in range(1, 6):
        repos.notificaciones.crear(notificacion(i, creada_en=AHORA + timedelta(minutes=i)))

    todas = repos.notificaciones.listar(CLIENTE)
    primera_pagina = repos.notificaciones.listar(CLIENTE, limite=2)
    segunda_pagina = repos.notificaciones.listar(CLIENTE, limite=2, desplazamiento=2)

    assert [n.notificacion_id for n in todas] == ["NOT-5", "NOT-4", "NOT-3", "NOT-2", "NOT-1"]
    assert [n.notificacion_id for n in primera_pagina] == ["NOT-5", "NOT-4"]
    assert [n.notificacion_id for n in segunda_pagina] == ["NOT-3", "NOT-2"]


def test_cada_cliente_ve_solo_sus_notificaciones(repos) -> None:
    repos.notificaciones.crear(notificacion(1))
    repos.notificaciones.crear(notificacion(2, cliente_id=OTRO))

    assert [n.notificacion_id for n in repos.notificaciones.listar(CLIENTE)] == ["NOT-1"]
    assert [n.notificacion_id for n in repos.notificaciones.listar(OTRO)] == ["NOT-2"]
    assert repos.notificaciones.listar("CLI-NADIE") == []


def test_cuenta_las_no_leidas_y_marcar_una_como_leida_la_descuenta(repos) -> None:
    repos.notificaciones.crear(notificacion(1))
    repos.notificaciones.crear(notificacion(2))
    assert repos.notificaciones.contar_no_leidas(CLIENTE) == 2

    cuando = AHORA + timedelta(hours=1)
    assert repos.notificaciones.marcar_leida(CLIENTE, "NOT-1", cuando) is True

    assert repos.notificaciones.contar_no_leidas(CLIENTE) == 1
    leida = repos.notificaciones.por_clave(CLIENTE, "SIN-1:APROBADO")
    assert leida.leida and leida.leida_en == cuando


def test_marcar_como_leida_dos_veces_conserva_la_primera_fecha(repos) -> None:
    repos.notificaciones.crear(notificacion(1))
    primera = AHORA + timedelta(hours=1)
    repos.notificaciones.marcar_leida(CLIENTE, "NOT-1", primera)

    assert repos.notificaciones.marcar_leida(CLIENTE, "NOT-1", primera + timedelta(hours=5))

    assert repos.notificaciones.por_clave(CLIENTE, "SIN-1:APROBADO").leida_en == primera


def test_no_se_marca_como_leida_la_de_otro_cliente_ni_una_inexistente(repos) -> None:
    repos.notificaciones.crear(notificacion(1))

    assert repos.notificaciones.marcar_leida(OTRO, "NOT-1", AHORA) is False
    assert repos.notificaciones.marcar_leida(CLIENTE, "NOT-NO", AHORA) is False
    assert repos.notificaciones.contar_no_leidas(CLIENTE) == 1


def test_cuenta_el_grupo_por_tipo_y_dia_de_cada_cliente(repos) -> None:
    siniestro = TipoNotificacion.ESTADO_SINIESTRO
    repos.notificaciones.crear(notificacion(1))
    repos.notificaciones.crear(notificacion(2))
    repos.notificaciones.crear(notificacion(3, tipo=TipoNotificacion.PAGO_PARAMETRICO))
    repos.notificaciones.crear(notificacion(4, dia=HOY - timedelta(days=1)))
    repos.notificaciones.crear(notificacion(5, cliente_id=OTRO))

    assert repos.notificaciones.contar_del_grupo(CLIENTE, siniestro, HOY) == 2
    assert repos.notificaciones.contar_del_grupo(CLIENTE, siniestro, HOY - timedelta(days=1)) == 1
    assert (
        repos.notificaciones.contar_del_grupo(CLIENTE, TipoNotificacion.PAGO_PARAMETRICO, HOY) == 1
    )
    assert (
        repos.notificaciones.contar_del_grupo(CLIENTE, TipoNotificacion.VENCIMIENTO_POLIZA, HOY)
        == 0
    )


# --- Dispositivos --------------------------------------------------------------------------


def test_registra_un_dispositivo_y_lo_lista_entre_los_activos(repos) -> None:
    guardado = repos.dispositivos.guardar(dispositivo("token-1"))

    assert guardado == dispositivo("token-1")
    assert repos.dispositivos.activos_de(CLIENTE) == [guardado]
    assert repos.dispositivos.activos_de(OTRO) == []


def test_registrar_el_mismo_token_no_duplica_el_dispositivo(repos) -> None:
    repos.dispositivos.guardar(dispositivo("token-1", numero=1))
    despues = repos.dispositivos.guardar(
        dispositivo("token-1", numero=2, actualizado_en=AHORA + timedelta(days=1))
    )

    activos = repos.dispositivos.activos_de(CLIENTE)
    assert len(activos) == 1
    assert despues.dispositivo_id == "DIS-1"  # conserva el del primer registro
    assert activos[0].actualizado_en == AHORA + timedelta(days=1)


def test_si_otro_cliente_inicia_sesion_en_el_telefono_el_token_pasa_a_el(repos) -> None:
    repos.dispositivos.guardar(dispositivo("token-compartido", cliente_id=CLIENTE))

    repos.dispositivos.guardar(dispositivo("token-compartido", cliente_id=OTRO, numero=2))

    assert repos.dispositivos.activos_de(CLIENTE) == []
    assert [d.token for d in repos.dispositivos.activos_de(OTRO)] == ["token-compartido"]


def test_un_cliente_puede_tener_varios_dispositivos(repos) -> None:
    repos.dispositivos.guardar(dispositivo("token-1", numero=1))
    repos.dispositivos.guardar(dispositivo("token-2", numero=2))

    assert sorted(d.token for d in repos.dispositivos.activos_de(CLIENTE)) == ["token-1", "token-2"]


def test_dar_de_baja_un_token_lo_saca_de_los_activos(repos) -> None:
    repos.dispositivos.guardar(dispositivo("token-1", numero=1))
    repos.dispositivos.guardar(dispositivo("token-2", numero=2))

    assert repos.dispositivos.desactivar(CLIENTE, "token-1", AHORA + timedelta(hours=1)) is True

    assert [d.token for d in repos.dispositivos.activos_de(CLIENTE)] == ["token-2"]


def test_no_se_da_de_baja_el_token_de_otro_cliente_ni_uno_desconocido(repos) -> None:
    repos.dispositivos.guardar(dispositivo("token-1"))

    assert repos.dispositivos.desactivar(OTRO, "token-1", AHORA) is False
    assert repos.dispositivos.desactivar(CLIENTE, "token-no", AHORA) is False
    assert len(repos.dispositivos.activos_de(CLIENTE)) == 1


def test_volver_a_registrar_un_token_dado_de_baja_lo_reactiva(repos) -> None:
    repos.dispositivos.guardar(dispositivo("token-1"))
    repos.dispositivos.desactivar(CLIENTE, "token-1", AHORA)

    repos.dispositivos.guardar(dispositivo("token-1", activo=True))

    assert len(repos.dispositivos.activos_de(CLIENTE)) == 1


# --- Preferencias --------------------------------------------------------------------------


def test_sin_preferencia_guardada_no_hay_nada(repos) -> None:
    assert repos.preferencias.obtener(CLIENTE) is None


def test_guarda_y_actualiza_la_preferencia_de_push(repos) -> None:
    repos.preferencias.guardar(preferencia(False))
    assert repos.preferencias.obtener(CLIENTE).push_habilitado is False

    repos.preferencias.guardar(preferencia(True))

    assert repos.preferencias.obtener(CLIENTE).push_habilitado is True
    assert repos.preferencias.obtener(OTRO) is None
