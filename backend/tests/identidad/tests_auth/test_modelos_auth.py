import pytest
from pydantic import ValidationError

from app.identidad.modelos import (
    SolicitudLogin,
    SolicitudRegistro,
)


def test_registro_rechaza_email_invalido():
    with pytest.raises(ValidationError):
        SolicitudRegistro(
            nombre="Ana",
            apellido="Perez",
            email="esto-no-es-un-email",
            password="Password123!",
            tipo_documento="CC",
            numero_documento="123456",
            fecha_nacimiento="1999-01-01",
            acepta_validacion_identidad=True,
        )


def test_registro_rechaza_password_menor_a_ocho():
    with pytest.raises(ValidationError):
        SolicitudRegistro(
            nombre="Ana",
            apellido="Perez",
            email="ana@gmail.com",
            password="123",
            tipo_documento="CC",
            numero_documento="123456",
            fecha_nacimiento="1999-01-01",
            acepta_validacion_identidad=True,
        )


def test_login_rechaza_email_invalido():
    with pytest.raises(ValidationError):
        SolicitudLogin(
            email="correo-invalido",
            password="Password123!",
        )


def test_login_acepta_datos_validos():
    solicitud = SolicitudLogin(
        email="ana@gmail.com",
        password="Password123!",
    )

    assert str(solicitud.email) == "ana@gmail.com"

    assert solicitud.password == "Password123!"
