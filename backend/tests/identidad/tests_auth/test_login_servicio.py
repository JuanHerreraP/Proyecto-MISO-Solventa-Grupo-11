from types import SimpleNamespace
from uuid import uuid4

import pytest

from pwdlib import PasswordHash

from app.identidad.servicio import (
    CredencialesInvalidasError,
    ServicioIdentidad,
    UsuarioInactivoError,
)


def _crear_usuario(
    password="Password123!",
    activo=True,
):
    password_hash = PasswordHash.recommended()

    return SimpleNamespace(
        id=uuid4(),
        email="ana@gmail.com",
        password_hash=password_hash.hash(
            password
        ),
        rol="CLIENTE",
        activo=activo,
    )


def test_login_exitoso_devuelve_token(
    repositorio,
    monkeypatch,
):
    usuario = _crear_usuario()

    repositorio.usuarios[
        "ana@gmail.com"
    ] = usuario

    def fake_crear_access_token(
        usuario_id,
        email,
        rol,
    ):
        return "jwt-falso-para-prueba"

    monkeypatch.setattr(
        "app.identidad.servicio.crear_access_token",
        fake_crear_access_token,
    )

    servicio = ServicioIdentidad(
        repositorio=repositorio
    )

    resultado = servicio.autenticar_usuario(
        email="ana@gmail.com",
        password="Password123!",
    )

    assert (
        resultado.access_token
        == "jwt-falso-para-prueba"
    )

    assert resultado.token_type == "bearer"

    assert resultado.expires_in == 1800


def test_login_correo_inexistente(
    repositorio,
):
    servicio = ServicioIdentidad(
        repositorio=repositorio
    )

    with pytest.raises(
        CredencialesInvalidasError
    ):
        servicio.autenticar_usuario(
            email="noexiste@gmail.com",
            password="Password123!",
        )


def test_login_password_incorrecto(
    repositorio,
):
    usuario = _crear_usuario()

    repositorio.usuarios[
        "ana@gmail.com"
    ] = usuario

    servicio = ServicioIdentidad(
        repositorio=repositorio
    )

    with pytest.raises(
        CredencialesInvalidasError
    ):
        servicio.autenticar_usuario(
            email="ana@gmail.com",
            password="incorrecta123",
        )


def test_usuario_inactivo_no_puede_iniciar_sesion(
    repositorio,
):
    usuario = _crear_usuario(
        activo=False
    )

    repositorio.usuarios[
        "ana@gmail.com"
    ] = usuario

    servicio = ServicioIdentidad(
        repositorio=repositorio
    )

    with pytest.raises(
        UsuarioInactivoError
    ):
        servicio.autenticar_usuario(
            email="ana@gmail.com",
            password="Password123!",
        )


def test_login_no_necesita_proveedor_kyc(
    repositorio,
    monkeypatch,
):
    usuario = _crear_usuario()

    repositorio.usuarios[
        "ana@gmail.com"
    ] = usuario

    monkeypatch.setattr(
        "app.identidad.servicio.crear_access_token",
        lambda usuario_id, email, rol: "token",
    )

    servicio = ServicioIdentidad(
        repositorio=repositorio,
        provider=None,
    )

    resultado = servicio.autenticar_usuario(
        email="ana@gmail.com",
        password="Password123!",
    )

    assert resultado.access_token == "token"