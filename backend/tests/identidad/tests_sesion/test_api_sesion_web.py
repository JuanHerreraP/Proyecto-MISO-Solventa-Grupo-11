"""Cookies, CSRF y CORS del navegador; conserva el contrato nativo de Android."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.identidad import auditoria
from app.identidad.modelos_db import EventoAutenticacionDB, SesionRefreshDB
from app.identidad.tokens import validar_refresh_token
from app.identidad.web import nombre_cookie
from app.infraestructura.database import get_db
from app.main import app
from tests.identidad.tests_sesion.conftest import PASSWORD, crear_usuario

RUTA = "/api/v1/auth/web"
ORIGEN = "http://localhost:5173"


@pytest.fixture
def api_web(fabrica_sesiones, db, monkeypatch):
    EventoAutenticacionDB.__table__.create(db.get_bind())
    monkeypatch.setattr(auditoria, "SessionLocal", fabrica_sesiones)
    monkeypatch.setenv("WEB_COOKIE_SECURE", "true")
    monkeypatch.setenv("WEB_COOKIE_SAMESITE", "lax")

    def obtener_db():
        with fabrica_sesiones() as sesion:
            yield sesion

    app.dependency_overrides[get_db] = obtener_db
    crear_usuario(db)
    try:
        with TestClient(app, base_url="https://api.solventa.test") as cliente:
            yield cliente
    finally:
        app.dependency_overrides.clear()


def cabeceras(cliente):
    respuesta = cliente.get(f"{RUTA}/csrf", headers={"Origin": ORIGEN})
    assert respuesta.status_code == 200
    return {"Origin": ORIGEN, "X-CSRF-Token": respuesta.json()["csrf_token"]}


def login(cliente):
    respuesta = cliente.post(
        f"{RUTA}/login",
        headers=cabeceras(cliente),
        json={"email": "ana@gmail.com", "password": PASSWORD},
    )
    assert respuesta.status_code == 200
    return respuesta


def test_login_guarda_refresh_solo_en_cookie_protegida(api_web):
    respuesta = login(api_web)
    assert set(respuesta.json()) == {"access_token", "token_type", "expires_in", "csrf_token"}
    assert respuesta.headers["Cache-Control"] == "no-store"
    cookies = respuesta.headers.get_list("set-cookie")
    for cookie in cookies:
        assert "HttpOnly" in cookie
        assert "Secure" in cookie
        assert "SameSite=lax" in cookie
        assert "Path=/" in cookie
        assert "Domain=" not in cookie
        assert cookie.startswith("__Host-")
    assert "Max-Age=604800" in cookies[0]
    refresh = api_web.cookies.get(nombre_cookie("refresh"))
    assert refresh
    assert refresh not in respuesta.text


def test_recarga_renueva_desde_cookie_y_rota_refresh(api_web, db):
    primera = login(api_web)
    anterior = api_web.cookies.get(nombre_cookie("refresh"))
    respuesta = api_web.post(f"{RUTA}/refresh", headers=cabeceras(api_web))
    assert respuesta.status_code == 200
    assert "refresh_token" not in respuesta.json()
    assert api_web.cookies.get(nombre_cookie("refresh")) != anterior
    almacenada = db.get(SesionRefreshDB, validar_refresh_token(anterior)["jti"])
    assert almacenada.revocada is True
    assert almacenada.motivo_revocacion == "ROTACION"
    perfil = api_web.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {respuesta.json()['access_token']}"}
    )
    assert perfil.status_code == 200
    assert (
        api_web.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {primera.json()['access_token']}"}
        ).status_code
        == 401
    )


@pytest.mark.parametrize("operacion", ["login", "refresh", "logout"])
@pytest.mark.parametrize("ataque", ["sin_csrf", "csrf_invalido", "origen_ajeno", "sin_origen"])
def test_csrf_rechaza_sin_modificar_sesion(api_web, operacion, ataque):
    login(api_web)
    anterior = api_web.cookies.get(nombre_cookie("refresh"))
    headers = cabeceras(api_web)
    if ataque == "sin_csrf":
        del headers["X-CSRF-Token"]
    elif ataque == "csrf_invalido":
        headers["X-CSRF-Token"] = "falso"
    elif ataque == "origen_ajeno":
        headers["Origin"] = "https://atacante.example"
    else:
        del headers["Origin"]
    respuesta = api_web.post(
        f"{RUTA}/{operacion}",
        headers=headers,
        json={"email": "ana@gmail.com", "password": PASSWORD},
    )
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"]["codigo"] == "CSRF_REJECTED"
    assert api_web.cookies.get(nombre_cookie("refresh")) == anterior
    assert "set-cookie" not in respuesta.headers


def test_refresh_no_acepta_token_en_el_cuerpo_sin_cookie(api_web):
    nativo = api_web.post(
        "/api/v1/auth/login", json={"email": "ana@gmail.com", "password": PASSWORD}
    )
    respuesta = api_web.post(
        f"{RUTA}/refresh",
        headers=cabeceras(api_web),
        json={"refresh_token": nativo.json()["refresh_token"]},
    )
    assert respuesta.status_code == 401


def test_logout_revoca_y_borra_cookies(api_web, db):
    sesion = login(api_web).json()
    refresh = api_web.cookies.get(nombre_cookie("refresh"))
    respuesta = api_web.post(f"{RUTA}/logout", headers=cabeceras(api_web))
    assert respuesta.status_code == 204
    assert all("Max-Age=0" in c for c in respuesta.headers.get_list("set-cookie"))
    assert api_web.cookies.get(nombre_cookie("refresh")) is None
    assert db.get(SesionRefreshDB, validar_refresh_token(refresh)["jti"]).revocada is True
    assert (
        api_web.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {sesion['access_token']}"}
        ).status_code
        == 401
    )


def test_cookie_no_supera_limite_de_inactividad(api_web, db):
    login(api_web)
    refresh = api_web.cookies.get(nombre_cookie("refresh"))
    sesion = db.get(SesionRefreshDB, validar_refresh_token(refresh)["jti"])
    sesion.ultima_actividad = datetime.now(timezone.utc) - timedelta(minutes=30)
    db.commit()
    respuesta = api_web.post(f"{RUTA}/refresh", headers=cabeceras(api_web))
    assert respuesta.status_code == 401
    assert api_web.cookies.get(nombre_cookie("refresh")) is None


def test_csrf_get_no_prolonga_la_sesion(api_web, db):
    login(api_web)
    refresh = api_web.cookies.get(nombre_cookie("refresh"))
    sesion = db.get(SesionRefreshDB, validar_refresh_token(refresh)["jti"])
    anterior = sesion.ultima_actividad
    cabeceras(api_web)
    db.refresh(sesion)
    assert sesion.ultima_actividad == anterior


def test_cors_solo_permite_origenes_explicitos(api_web):
    headers = {
        "Origin": ORIGEN,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-csrf-token",
    }
    respuesta = api_web.options(f"{RUTA}/refresh", headers=headers)
    assert respuesta.status_code == 200
    assert respuesta.headers["Access-Control-Allow-Origin"] == ORIGEN
    assert respuesta.headers["Access-Control-Allow-Credentials"] == "true"
    headers["Origin"] = "https://atacante.example"
    respuesta = api_web.options(f"{RUTA}/refresh", headers=headers)
    assert respuesta.status_code == 400
    assert "Access-Control-Allow-Origin" not in respuesta.headers


def test_contrato_android_se_conserva(api_web):
    respuesta = api_web.post(
        "/api/v1/auth/login", json={"email": "ana@gmail.com", "password": PASSWORD}
    )
    assert respuesta.status_code == 200
    assert "set-cookie" not in respuesta.headers
    token = respuesta.json()["refresh_token"]
    assert api_web.post("/api/v1/auth/refresh", json={"refresh_token": token}).status_code == 200


def test_configuracion_rechaza_cors_con_comodin(monkeypatch):
    from app.identidad.web import origenes_web

    monkeypatch.setenv("WEB_ALLOWED_ORIGINS", "*")
    with pytest.raises(ValueError):
        origenes_web()


def test_produccion_no_admite_cookie_insegura(monkeypatch):
    from app.identidad.web import opciones_cookie

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("WEB_COOKIE_SECURE", "false")
    with pytest.raises(ValueError):
        opciones_cookie()


def test_same_site_none_requiere_secure(monkeypatch):
    from app.identidad.web import opciones_cookie

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("WEB_COOKIE_SECURE", "false")
    monkeypatch.setenv("WEB_COOKIE_SAMESITE", "none")
    with pytest.raises(ValueError):
        opciones_cookie()
