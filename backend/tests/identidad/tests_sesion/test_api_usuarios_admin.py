"""Autorización de la administración de usuarios y asignación de roles."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api import autenticacion, seguridad
from app.identidad.config import get_identity_verification_provider
from app.identidad.modelos import Rol, VerificationResult, VerificationStatus
from app.identidad.tokens import crear_access_token
from app.infraestructura.database import get_db
from app.main import app
from tests.identidad.tests_sesion.conftest import crear_usuario

RUTA = "/api/v1/auth/users"


@pytest.fixture
def cliente(fabrica_sesiones, monkeypatch):
    for modulo in (autenticacion, seguridad):
        monkeypatch.setattr(modulo, "registrar_evento_auth", lambda **kw: None)

    class Provider:
        def verify(self, solicitud):
            return VerificationResult(
                "KYC-ADMIN", VerificationStatus.APPROVED, 0.1,
                "test", datetime.now(timezone.utc),
            )

    def obtener_db():
        with fabrica_sesiones() as sesion:
            yield sesion

    app.dependency_overrides[get_db] = obtener_db
    app.dependency_overrides[get_identity_verification_provider] = Provider
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def cabecera(db, rol):
    usuario = crear_usuario(db)
    usuario.rol = rol.value
    db.commit()
    token = crear_access_token(str(usuario.id), usuario.email, rol.value)
    return {"Authorization": f"Bearer {token}"}


def solicitud(rol):
    return {
        "nombre": "Nuevo", "apellido": "Usuario", "email": "nuevo@example.com",
        "password": "Password123!", "tipo_documento": "CC",
        "numero_documento": "123456789", "fecha_nacimiento": "1990-01-01",
        "acepta_validacion_identidad": True, "rol": rol,
    }


@pytest.mark.parametrize("rol", list(Rol))
def test_manager_crea_cualquier_rol(cliente, db, rol):
    headers = cabecera(db, Rol.SERVICIO_INTERNO)
    respuesta = cliente.post(RUTA, headers=headers, json=solicitud(rol.value))
    assert respuesta.status_code == 201
    assert respuesta.json()["rol"] == rol.value
    assert "password_hash" not in respuesta.json()
    assert cliente.get(RUTA, headers=headers).status_code == 200
    assert cliente.post(RUTA, headers=headers, json=solicitud(rol.value)).status_code == 409


@pytest.mark.parametrize("rol", [r for r in Rol if r != Rol.SERVICIO_INTERNO])
def test_otros_roles_no_administran(cliente, db, rol):
    headers = cabecera(db, rol)
    assert cliente.post(RUTA, headers=headers, json=solicitud("CLIENTE")).status_code == 403
    assert cliente.get(RUTA, headers=headers).status_code == 403


def test_sin_token_no_administra(cliente):
    assert cliente.post(RUTA, json=solicitud("CLIENTE")).status_code == 401
    assert cliente.get(RUTA).status_code == 401


def test_rol_desconocido_rechazado(cliente, db):
    headers = cabecera(db, Rol.SERVICIO_INTERNO)
    assert cliente.post(RUTA, headers=headers, json=solicitud("SUPERADMIN")).status_code == 422


def test_registro_publico_no_escala_rol(cliente):
    respuesta = cliente.post("/api/v1/auth/register", json=solicitud("SERVICIO_INTERNO"))
    assert respuesta.status_code == 201
    assert respuesta.json()["rol"] == "CLIENTE"
