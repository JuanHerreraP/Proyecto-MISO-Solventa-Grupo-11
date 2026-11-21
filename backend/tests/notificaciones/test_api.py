"""API de notificaciones: bandeja, dispositivos push y preferencia (HU05)."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.cotizaciones import ActorCotizacion, TipoActorCotizacion, actor_actual
from app.api.notificaciones import obtener_servicio
from app.identidad.modelos import Rol
from app.main import app
from app.notificaciones.bandeja import ServicioBandeja
from app.notificaciones.modelos import MotivoSinPush, TipoNotificacion
from app.notificaciones.repositorio import RepositorioNotificacionesPostgres
from tests.notificaciones.fabrica import (
    AHORA,
    CLIENTE,
    OTRO,
    Reloj,
    crear_servicio,
    notificacion,
    repositorios_en_memoria,
)

RUTA = "/api/v1/notificaciones"
TOKEN = "fcm-token-secreto-de-un-telefono-0001"


def actor(rol=Rol.CLIENTE, actor_id=CLIENTE, tipo=TipoActorCotizacion.USUARIO):
    return lambda: ActorCotizacion(tipo=tipo, actor_id=actor_id, rol=rol)


@pytest.fixture
def entorno():
    repos = repositorios_en_memoria()
    reloj = Reloj()
    servicio = ServicioBandeja(
        repos.notificaciones,
        repos.dispositivos,
        repos.preferencias,
        reloj=reloj,
        generar_id=iter(f"DIS-{n}" for n in range(1, 100)).__next__,
    )
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    app.dependency_overrides[actor_actual] = actor()
    yield TestClient(app), repos, reloj
    app.dependency_overrides.clear()


def como(actor_id: str = CLIENTE, **argumentos):
    app.dependency_overrides[actor_actual] = actor(actor_id=actor_id, **argumentos)


# --- Bandeja -------------------------------------------------------------------------------


def test_lista_las_notificaciones_del_cliente_la_mas_reciente_primero(entorno) -> None:
    cliente, repos, _ = entorno
    for i in range(1, 4):
        repos.notificaciones.crear(notificacion(i, creada_en=AHORA + timedelta(minutes=i)))
    repos.notificaciones.crear(notificacion(9, cliente_id=OTRO))

    respuesta = cliente.get(RUTA)

    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert [n["notificacion_id"] for n in cuerpo["notificaciones"]] == ["NOT-3", "NOT-2", "NOT-1"]
    assert cuerpo["no_leidas"] == 3


def test_cada_notificacion_trae_lo_necesario_y_no_datos_internos(entorno) -> None:
    cliente, repos, _ = entorno
    repos.notificaciones.crear(
        notificacion(1, tipo=TipoNotificacion.PAGO_PARAMETRICO, datos={"siniestro_id": "SIN-1"})
    )

    (n,) = cliente.get(RUTA).json()["notificaciones"]

    assert n["tipo"] == "PAGO_PARAMETRICO"
    assert n["titulo"] and n["cuerpo"]
    assert n["datos"] == {"siniestro_id": "SIN-1"}
    assert n["leida"] is False and n["leida_en"] is None
    for interno in ("cliente_id", "clave", "dia"):
        assert interno not in n


def test_pagina_y_cuenta_todas_las_no_leidas_no_solo_las_de_la_pagina(entorno) -> None:
    cliente, repos, _ = entorno
    for i in range(1, 6):
        repos.notificaciones.crear(notificacion(i, creada_en=AHORA + timedelta(minutes=i)))

    pagina = cliente.get(RUTA, params={"limite": 2, "desplazamiento": 2}).json()

    assert [n["notificacion_id"] for n in pagina["notificaciones"]] == ["NOT-3", "NOT-2"]
    assert pagina["no_leidas"] == 5


@pytest.mark.parametrize(
    "parametros", [{"limite": 0}, {"limite": 101}, {"desplazamiento": -1}, {"limite": "x"}]
)
def test_rechaza_parametros_de_paginacion_invalidos(entorno, parametros) -> None:
    cliente, _, _ = entorno

    assert cliente.get(RUTA, params=parametros).status_code == 422


def test_sin_notificaciones_la_lista_esta_vacia(entorno) -> None:
    cliente, _, _ = entorno

    assert cliente.get(RUTA).json() == {"notificaciones": [], "no_leidas": 0}


def test_cuenta_las_no_leidas_para_la_insignia(entorno) -> None:
    cliente, repos, _ = entorno
    repos.notificaciones.crear(notificacion(1))
    repos.notificaciones.crear(notificacion(2))
    repos.notificaciones.crear(notificacion(3, cliente_id=OTRO))

    respuesta = cliente.get(f"{RUTA}/no-leidas")

    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {"no_leidas": 2}


def test_marca_una_notificacion_como_leida_y_descuenta_la_insignia(entorno) -> None:
    cliente, repos, reloj = entorno
    repos.notificaciones.crear(notificacion(1))
    repos.notificaciones.crear(notificacion(2))

    respuesta = cliente.post(f"{RUTA}/NOT-1/leida")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"notificacion_id": "NOT-1", "leida": True, "no_leidas": 1}
    por_id = {n["notificacion_id"]: n for n in cliente.get(RUTA).json()["notificaciones"]}
    assert por_id["NOT-1"]["leida"] is True
    assert por_id["NOT-1"]["leida_en"].startswith(reloj.ahora.strftime("%Y-%m-%dT%H:%M"))
    assert por_id["NOT-2"]["leida"] is False


def test_marcarla_leida_dos_veces_no_cambia_nada(entorno) -> None:
    cliente, repos, _ = entorno
    repos.notificaciones.crear(notificacion(1))
    cliente.post(f"{RUTA}/NOT-1/leida")

    segunda = cliente.post(f"{RUTA}/NOT-1/leida")

    assert segunda.status_code == 200 and segunda.json()["no_leidas"] == 0


def test_una_notificacion_ajena_o_inexistente_responde_404(entorno) -> None:
    cliente, repos, _ = entorno
    repos.notificaciones.crear(notificacion(1, cliente_id=OTRO))

    ajena = cliente.post(f"{RUTA}/NOT-1/leida")
    inexistente = cliente.post(f"{RUTA}/NOT-NO/leida")

    for respuesta in (ajena, inexistente):
        assert respuesta.status_code == 404
        assert respuesta.json()["detail"]["codigo"] == "NOTIFICACION_NO_ENCONTRADA"
    # La del otro cliente sigue sin leer: no se pudo marcar desde fuera.
    assert repos.notificaciones.contar_no_leidas(OTRO) == 1


# --- Dispositivos --------------------------------------------------------------------------


def test_registra_el_token_del_telefono(entorno) -> None:
    cliente, repos, _ = entorno

    respuesta = cliente.put(f"{RUTA}/dispositivos", json={"token": TOKEN})

    assert respuesta.status_code == 204 and respuesta.content == b""
    (dispositivo,) = repos.dispositivos.activos_de(CLIENTE)
    assert dispositivo.token == TOKEN and dispositivo.plataforma == "ANDROID"


def test_registrar_el_mismo_token_otra_vez_no_lo_duplica(entorno) -> None:
    cliente, repos, _ = entorno
    cliente.put(f"{RUTA}/dispositivos", json={"token": TOKEN})

    cliente.put(f"{RUTA}/dispositivos", json={"token": TOKEN, "plataforma": "ANDROID"})

    assert len(repos.dispositivos.activos_de(CLIENTE)) == 1


def test_un_cliente_puede_registrar_varios_telefonos(entorno) -> None:
    cliente, repos, _ = entorno

    cliente.put(f"{RUTA}/dispositivos", json={"token": TOKEN})
    cliente.put(f"{RUTA}/dispositivos", json={"token": "otro-telefono-0002"})

    assert len(repos.dispositivos.activos_de(CLIENTE)) == 2


def test_si_otro_cliente_inicia_sesion_en_el_telefono_el_token_pasa_a_el(entorno) -> None:
    cliente, repos, _ = entorno
    cliente.put(f"{RUTA}/dispositivos", json={"token": TOKEN})

    como(OTRO)
    cliente.put(f"{RUTA}/dispositivos", json={"token": TOKEN})

    assert repos.dispositivos.activos_de(CLIENTE) == []
    assert [d.token for d in repos.dispositivos.activos_de(OTRO)] == [TOKEN]


@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {"token": ""},
        {"token": "   "},
        {"token": "t" * 513},
        {"token": TOKEN, "plataforma": "android"},
        {"token": TOKEN, "otro": 1},
    ],
)
def test_rechaza_solicitudes_de_dispositivo_invalidas_sin_devolver_el_token(
    entorno, cuerpo
) -> None:
    cliente, repos, _ = entorno

    respuesta = cliente.put(f"{RUTA}/dispositivos", json=cuerpo)

    assert respuesta.status_code == 422
    assert all("input" not in error for error in respuesta.json()["detail"])
    assert TOKEN not in respuesta.text
    assert repos.dispositivos.activos_de(CLIENTE) == []


def test_da_de_baja_el_token_y_ya_no_se_le_manda_push(entorno) -> None:
    cliente, repos, _ = entorno
    cliente.put(f"{RUTA}/dispositivos", json={"token": TOKEN})
    servicio, _, _ = crear_servicio(repos)

    respuesta = cliente.post(f"{RUTA}/dispositivos/baja", json={"token": TOKEN})

    assert respuesta.status_code == 204
    assert repos.dispositivos.activos_de(CLIENTE) == []
    registro = servicio.registrar(
        CLIENTE, TipoNotificacion.ESTADO_SINIESTRO, "SIN-1:X", "Título", "Cuerpo"
    )
    assert registro.motivo_sin_push is MotivoSinPush.SIN_DISPOSITIVOS


def test_la_baja_es_tolerante_con_un_token_desconocido_o_ajeno(entorno) -> None:
    cliente, repos, _ = entorno
    como(OTRO)
    cliente.put(f"{RUTA}/dispositivos", json={"token": TOKEN})
    como(CLIENTE)

    desconocido = cliente.post(f"{RUTA}/dispositivos/baja", json={"token": "no-existe"})
    ajeno = cliente.post(f"{RUTA}/dispositivos/baja", json={"token": TOKEN})

    assert desconocido.status_code == 204 and ajeno.status_code == 204
    # El token ajeno sigue activo: nadie puede apagar el teléfono de otro cliente.
    assert [d.token for d in repos.dispositivos.activos_de(OTRO)] == [TOKEN]


def test_la_baja_rechaza_un_cuerpo_invalido_sin_devolver_el_token(entorno) -> None:
    cliente, _, _ = entorno

    respuesta = cliente.post(f"{RUTA}/dispositivos/baja", json={"token": "t" * 600})

    assert respuesta.status_code == 422 and "t" * 600 not in respuesta.text


# --- Preferencia ---------------------------------------------------------------------------


def test_por_defecto_el_push_esta_habilitado(entorno) -> None:
    cliente, _, _ = entorno

    respuesta = cliente.get(f"{RUTA}/preferencias")

    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {"push_habilitado": True}


def test_deshabilitar_el_push_se_conserva_y_se_puede_volver_a_habilitar(entorno) -> None:
    cliente, _, _ = entorno

    apagado = cliente.put(f"{RUTA}/preferencias", json={"push_habilitado": False})
    consulta = cliente.get(f"{RUTA}/preferencias")
    cliente.put(f"{RUTA}/preferencias", json={"push_habilitado": True})

    assert apagado.json() == {"push_habilitado": False}
    assert consulta.json() == {"push_habilitado": False}
    assert cliente.get(f"{RUTA}/preferencias").json() == {"push_habilitado": True}


def test_con_el_push_deshabilitado_los_eventos_siguen_apareciendo_en_la_bandeja(entorno) -> None:
    cliente, repos, _ = entorno
    cliente.put(f"{RUTA}/dispositivos", json={"token": TOKEN})
    cliente.put(f"{RUTA}/preferencias", json={"push_habilitado": False})
    servicio, _, _ = crear_servicio(repos)

    registro = servicio.registrar(
        CLIENTE, TipoNotificacion.PAGO_PARAMETRICO, "SIN-1:PAGO", "Pago", "Recibiste un pago"
    )

    assert registro.push is None and registro.motivo_sin_push is MotivoSinPush.PUSH_DESHABILITADO
    (n,) = cliente.get(RUTA).json()["notificaciones"]
    assert n["titulo"] == "Pago" and n["leida"] is False


def test_la_preferencia_es_de_cada_cliente(entorno) -> None:
    cliente, _, _ = entorno
    cliente.put(f"{RUTA}/preferencias", json={"push_habilitado": False})

    como(OTRO)

    assert cliente.get(f"{RUTA}/preferencias").json() == {"push_habilitado": True}


@pytest.mark.parametrize(
    "cuerpo", [{}, {"push_habilitado": "tal vez"}, {"push_habilitado": True, "x": 1}]
)
def test_rechaza_una_preferencia_invalida(entorno, cuerpo) -> None:
    cliente, _, _ = entorno

    assert cliente.put(f"{RUTA}/preferencias", json=cuerpo).status_code == 422


# --- Acceso --------------------------------------------------------------------------------

ENDPOINTS = [
    ("get", RUTA, None),
    ("get", f"{RUTA}/no-leidas", None),
    ("post", f"{RUTA}/NOT-1/leida", None),
    ("put", f"{RUTA}/dispositivos", {"token": TOKEN}),
    ("post", f"{RUTA}/dispositivos/baja", {"token": TOKEN}),
    ("get", f"{RUTA}/preferencias", None),
    ("put", f"{RUTA}/preferencias", {"push_habilitado": False}),
]


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo"), ENDPOINTS)
def test_solo_el_cliente_puede_usar_estos_endpoints(entorno, metodo, ruta, cuerpo) -> None:
    cliente, _, _ = entorno

    for rol in (Rol.ASESOR_VENTAS, Rol.ANALISTA_RIESGOS):
        como("OTRO-ACTOR", rol=rol)
        assert cliente.request(metodo.upper(), ruta, json=cuerpo).status_code == 403
    como("SOCIO-1", rol=None, tipo=TipoActorCotizacion.SOCIO)
    assert cliente.request(metodo.upper(), ruta, json=cuerpo).status_code == 403


def test_sin_sesion_responde_401() -> None:
    app.dependency_overrides.clear()

    assert TestClient(app).get(RUTA).status_code == 401


def test_las_rutas_fijas_no_se_confunden_con_una_notificacion(entorno) -> None:
    cliente, _, _ = entorno

    # `preferencias` y `no-leidas` son rutas propias, no ids: no responden 404 de notificación.
    assert cliente.get(f"{RUTA}/preferencias").status_code == 200
    assert cliente.get(f"{RUTA}/no-leidas").status_code == 200


# --- Cableado real con base de datos -------------------------------------------------------


def test_el_cableado_real_funciona_de_punta_a_punta_con_la_base() -> None:
    from app.infraestructura.database import Base, get_db

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sesion = sessionmaker(bind=engine)()
    RepositorioNotificacionesPostgres(sesion).crear(notificacion(1))
    app.dependency_overrides[get_db] = lambda: sesion
    app.dependency_overrides[actor_actual] = actor()
    try:
        cliente = TestClient(app)
        assert cliente.put(f"{RUTA}/dispositivos", json={"token": TOKEN}).status_code == 204
        assert (
            cliente.put(f"{RUTA}/preferencias", json={"push_habilitado": False}).status_code == 200
        )
        assert cliente.get(f"{RUTA}/preferencias").json() == {"push_habilitado": False}
        assert cliente.get(f"{RUTA}/no-leidas").json() == {"no_leidas": 1}
        assert len(cliente.get(RUTA).json()["notificaciones"]) == 1
        assert cliente.post(f"{RUTA}/NOT-1/leida").json()["no_leidas"] == 0
        assert cliente.post(f"{RUTA}/dispositivos/baja", json={"token": TOKEN}).status_code == 204
    finally:
        app.dependency_overrides.clear()
        sesion.close()
        engine.dispose()
