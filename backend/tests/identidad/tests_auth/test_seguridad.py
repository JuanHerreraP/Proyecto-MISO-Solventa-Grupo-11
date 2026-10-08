from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api import seguridad
from app.api.seguridad import Rol
from app.identidad.tokens import (
    TokenExpiradoError,
    TokenInvalidoError,
)


class FakeRepositorioUsuarios:
    def __init__(self, db):
        self.db = db

    def buscar_por_id(self, usuario_id):
        return getattr(
            self.db,
            "usuario",
            None,
        )


def _credentials(token="token-prueba"):
    return HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )


def _request():
    return SimpleNamespace(
        client=SimpleNamespace(
            host="127.0.0.1"
        ),
        headers={
            "user-agent": "pytest"
        },
    )


def test_get_current_user_rechaza_sin_token(
    monkeypatch,
):
    eventos = []

    monkeypatch.setattr(
        seguridad,
        "registrar_evento_auth",
        lambda **kwargs: eventos.append(
            kwargs
        ),
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        seguridad.get_current_user(
            request=_request(),
            credentials=None,
            db=SimpleNamespace(),
        )

    assert exc.value.status_code == 401

    assert (
        exc.value.detail["codigo"]
        == "TOKEN_REQUIRED"
    )

    assert len(eventos) == 1

    assert (
        eventos[0]["tipo_evento"]
        == seguridad.TipoEventoAuth.TOKEN_REQUIRED
    )


def test_get_current_user_rechaza_token_expirado(
    monkeypatch,
):
    eventos = []

    def fake_validar(token):
        raise TokenExpiradoError(
            "El token de acceso ha expirado."
        )

    monkeypatch.setattr(
        seguridad,
        "validar_access_token",
        fake_validar,
    )

    monkeypatch.setattr(
        seguridad,
        "registrar_evento_auth",
        lambda **kwargs: eventos.append(
            kwargs
        ),
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        seguridad.get_current_user(
            request=_request(),
            credentials=_credentials(),
            db=SimpleNamespace(),
        )

    assert exc.value.status_code == 401

    assert (
        exc.value.detail["codigo"]
        == "TOKEN_EXPIRED"
    )

    assert len(eventos) == 1

    assert (
        eventos[0]["tipo_evento"]
        == seguridad.TipoEventoAuth.TOKEN_EXPIRED
    )


def test_get_current_user_rechaza_token_invalido(
    monkeypatch,
):
    eventos = []

    def fake_validar(token):
        raise TokenInvalidoError(
            "El token de acceso no es válido."
        )

    monkeypatch.setattr(
        seguridad,
        "validar_access_token",
        fake_validar,
    )

    monkeypatch.setattr(
        seguridad,
        "registrar_evento_auth",
        lambda **kwargs: eventos.append(
            kwargs
        ),
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        seguridad.get_current_user(
            request=_request(),
            credentials=_credentials(),
            db=SimpleNamespace(),
        )

    assert exc.value.status_code == 401

    assert (
        exc.value.detail["codigo"]
        == "TOKEN_INVALID"
    )

    assert len(eventos) == 1


def test_get_current_user_rechaza_usuario_inexistente(
    monkeypatch,
):
    eventos = []

    monkeypatch.setattr(
        seguridad,
        "validar_access_token",
        lambda token: {
            "sub": "usuario-123",
            "email": "ana@gmail.com",
        },
    )

    monkeypatch.setattr(
        seguridad,
        "RepositorioUsuariosPostgres",
        FakeRepositorioUsuarios,
    )

    monkeypatch.setattr(
        seguridad,
        "registrar_evento_auth",
        lambda **kwargs: eventos.append(
            kwargs
        ),
    )

    db = SimpleNamespace(
        usuario=None
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        seguridad.get_current_user(
            request=_request(),
            credentials=_credentials(),
            db=db,
        )

    assert exc.value.status_code == 401

    assert (
        exc.value.detail["codigo"]
        == "USER_NOT_FOUND"
    )


def test_get_current_user_rechaza_usuario_inactivo(
    monkeypatch,
):
    eventos = []

    usuario = SimpleNamespace(
        id="usuario-123",
        email="ana@gmail.com",
        rol="CLIENTE",
        activo=False,
    )

    monkeypatch.setattr(
        seguridad,
        "validar_access_token",
        lambda token: {
            "sub": "usuario-123",
            "email": "ana@gmail.com",
        },
    )

    monkeypatch.setattr(
        seguridad,
        "RepositorioUsuariosPostgres",
        FakeRepositorioUsuarios,
    )

    monkeypatch.setattr(
        seguridad,
        "registrar_evento_auth",
        lambda **kwargs: eventos.append(
            kwargs
        ),
    )

    db = SimpleNamespace(
        usuario=usuario
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        seguridad.get_current_user(
            request=_request(),
            credentials=_credentials(),
            db=db,
        )

    assert exc.value.status_code == 403

    assert (
        exc.value.detail["codigo"]
        == "USER_INACTIVE"
    )

    assert (
        eventos[0]["tipo_evento"]
        == seguridad.TipoEventoAuth.ACCESS_DENIED
    )


def test_get_current_user_retorna_usuario_valido(
    monkeypatch,
):
    usuario = SimpleNamespace(
        id="usuario-123",
        email="ana@gmail.com",
        rol="CLIENTE",
        activo=True,
    )

    monkeypatch.setattr(
        seguridad,
        "validar_access_token",
        lambda token: {
            "sub": "usuario-123",
            "email": "ana@gmail.com",
            "rol": "CLIENTE",
        },
    )

    monkeypatch.setattr(
        seguridad,
        "RepositorioUsuariosPostgres",
        FakeRepositorioUsuarios,
    )

    db = SimpleNamespace(
        usuario=usuario
    )

    resultado = (
        seguridad.get_current_user(
            request=_request(),
            credentials=_credentials(),
            db=db,
        )
    )

    assert resultado is usuario
    assert resultado.email == "ana@gmail.com"
    assert resultado.activo is True



def test_rol_actual_se_obtiene_del_usuario():
    usuario = SimpleNamespace(
        rol="CLIENTE"
    )

    resultado = seguridad.rol_actual(
        usuario=usuario
    )

    assert resultado == Rol.CLIENTE


def test_rol_actual_analista_riesgos():
    usuario = SimpleNamespace(
        rol="ANALISTA_RIESGOS"
    )

    resultado = seguridad.rol_actual(
        usuario=usuario
    )

    assert (
        resultado
        == Rol.ANALISTA_RIESGOS
    )


def test_rol_actual_rechaza_rol_desconocido():
    usuario = SimpleNamespace(
        rol="SUPER_ADMIN_INVENTADO"
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        seguridad.rol_actual(
            usuario=usuario
        )

    assert exc.value.status_code == 403

    assert (
        exc.value.detail["codigo"]
        == "ROLE_INVALID"
    )

    def test_requiere_roles_permite_rol_autorizado(
    monkeypatch,
    ):
        usuario = SimpleNamespace(
            id="usuario-1",
            email="analista@solventa.com",
            rol="ANALISTA_RIESGOS",
        )

        dependencia = (
            seguridad.requiere_roles(
                "ANALISTA_RIESGOS",
                "OPERACIONES_SINIESTROS",
            )
        )

        resultado = dependencia(
            request=_request(),
            usuario=usuario,
        )

        assert resultado is usuario


    def test_requiere_roles_rechaza_rol_no_autorizado(
        monkeypatch,
    ):
        eventos = []

        usuario = SimpleNamespace(
            id="usuario-1",
            email="cliente@solventa.com",
            rol="CLIENTE",
        )

        monkeypatch.setattr(
            seguridad,
            "registrar_evento_auth",
            lambda **kwargs: eventos.append(
                kwargs
            ),
        )

        dependencia = (
            seguridad.requiere_roles(
                "ANALISTA_RIESGOS",
            )
        )

        with pytest.raises(
            HTTPException
        ) as exc:
            dependencia(
                request=_request(),
                usuario=usuario,
            )

        assert exc.value.status_code == 403

        assert (
            exc.value.detail["codigo"]
            == "ACCESS_DENIED"
        )

        assert len(eventos) == 1

        assert (
            eventos[0]["tipo_evento"]
            == seguridad.TipoEventoAuth.ACCESS_DENIED
        )