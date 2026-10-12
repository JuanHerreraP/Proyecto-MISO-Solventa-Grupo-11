"""HU02 (BPM-23): endpoints /auth/refresh, /auth/logout y /auth/me."""

import pytest
from fastapi.testclient import TestClient

from app.api import autenticacion, seguridad
from app.identidad import tokens
from app.infraestructura.database import get_db
from app.main import app
from tests.identidad.tests_sesion.conftest import PASSWORD, crear_usuario

RUTA = "/api/v1/auth"


@pytest.fixture
def eventos(monkeypatch):
    registrados = []
    monkeypatch.setattr(autenticacion, "registrar_evento_auth", lambda **kw: registrados.append(kw))
    monkeypatch.setattr(seguridad, "registrar_evento_auth", lambda **kw: registrados.append(kw))
    return registrados


@pytest.fixture
def cliente(fabrica_sesiones, eventos):
    def db_de_prueba():
        with fabrica_sesiones() as sesion:
            yield sesion

    app.dependency_overrides[get_db] = db_de_prueba
    yield TestClient(app)
    app.dependency_overrides.clear()


def _login(cliente, email="ana@gmail.com") -> dict:
    respuesta = cliente.post(f"{RUTA}/login", json={"email": email, "password": PASSWORD})
    assert respuesta.status_code == 200
    return respuesta.json()


def test_me_devuelve_solo_los_datos_del_duenio_del_token(cliente, db):
    crear_usuario(db, email="ana@gmail.com")
    crear_usuario(db, email="luis@gmail.com")
    sesion = _login(cliente, "ana@gmail.com")

    respuesta = cliente.get(
        f"{RUTA}/me", headers={"Authorization": f"Bearer {sesion['access_token']}"}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["email"] == "ana@gmail.com"
    assert set(cuerpo) == {"id", "nombre", "apellido", "email", "rol"}


def test_me_sin_token_no_expone_datos(cliente):
    respuesta = cliente.get(f"{RUTA}/me")

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"]["codigo"] == "TOKEN_REQUIRED"


def test_me_con_token_expirado_responde_401(cliente, db, monkeypatch):
    crear_usuario(db)
    monkeypatch.setattr(tokens, "ACCESS_TOKEN_MINUTES", -1)
    sesion = _login(cliente)

    respuesta = cliente.get(
        f"{RUTA}/me", headers={"Authorization": f"Bearer {sesion['access_token']}"}
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"]["codigo"] == "TOKEN_EXPIRED"


def test_refresh_entrega_tokens_nuevos(cliente, db, eventos):
    crear_usuario(db)
    sesion = _login(cliente)

    respuesta = cliente.post(f"{RUTA}/refresh", json={"refresh_token": sesion["refresh_token"]})

    assert respuesta.status_code == 200
    assert respuesta.json()["refresh_token"] != sesion["refresh_token"]
    assert eventos[-1]["tipo_evento"].value == "TOKEN_REFRESHED"


def test_refresh_reutilizado_responde_401_y_audita(cliente, db, eventos):
    crear_usuario(db)
    sesion = _login(cliente)
    cliente.post(f"{RUTA}/refresh", json={"refresh_token": sesion["refresh_token"]})

    respuesta = cliente.post(f"{RUTA}/refresh", json={"refresh_token": sesion["refresh_token"]})

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"]["codigo"] == "REFRESH_REUSED"
    assert eventos[-1]["tipo_evento"].value == "REFRESH_REUSE_DETECTED"


def test_refresh_expirado_responde_401(cliente, db, monkeypatch):
    crear_usuario(db)
    monkeypatch.setattr(tokens, "REFRESH_TOKEN_DAYS", -1)
    sesion = _login(cliente)

    respuesta = cliente.post(f"{RUTA}/refresh", json={"refresh_token": sesion["refresh_token"]})

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"]["codigo"] == "REFRESH_EXPIRED"


def test_refresh_invalido_responde_401(cliente):
    respuesta = cliente.post(f"{RUTA}/refresh", json={"refresh_token": "no-es-un-jwt"})

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"]["codigo"] == "REFRESH_INVALID"


def test_refresh_vacio_se_rechaza(cliente):
    assert cliente.post(f"{RUTA}/refresh", json={"refresh_token": ""}).status_code == 422


def test_refresh_de_usuario_inactivo_responde_403(cliente, db):
    usuario = crear_usuario(db)
    sesion = _login(cliente)
    usuario.activo = False
    db.commit()

    respuesta = cliente.post(f"{RUTA}/refresh", json={"refresh_token": sesion["refresh_token"]})

    assert respuesta.status_code == 403
    assert respuesta.json()["detail"]["codigo"] == "USER_INACTIVE"


def test_logout_cierra_la_sesion(cliente, db, eventos):
    crear_usuario(db)
    sesion = _login(cliente)

    respuesta = cliente.post(f"{RUTA}/logout", json={"refresh_token": sesion["refresh_token"]})

    assert respuesta.status_code == 204
    assert eventos[-1]["tipo_evento"].value == "LOGOUT"
    despues = cliente.post(f"{RUTA}/refresh", json={"refresh_token": sesion["refresh_token"]})
    assert despues.status_code == 401
    assert despues.json()["detail"]["codigo"] == "REFRESH_INVALID"


def test_logout_dos_veces_responde_204(cliente, db):
    crear_usuario(db)
    sesion = _login(cliente)
    cuerpo = {"refresh_token": sesion["refresh_token"]}

    assert cliente.post(f"{RUTA}/logout", json=cuerpo).status_code == 204
    assert cliente.post(f"{RUTA}/logout", json=cuerpo).status_code == 204


def test_logout_con_token_invalido_responde_401(cliente):
    respuesta = cliente.post(f"{RUTA}/logout", json={"refresh_token": "basura"})

    assert respuesta.status_code == 401
