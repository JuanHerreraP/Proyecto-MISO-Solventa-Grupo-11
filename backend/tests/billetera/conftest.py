from types import SimpleNamespace

import pytest
from fastapi import Header, HTTPException, status

from app.api.seguridad import get_current_user
from app.identidad.modelos import Rol
from app.main import app


def usuario_para_pruebas(
    x_rol: str | None = Header(default=None),
    x_usuario: str = Header(default="CLI-001"),
):
    if x_rol is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta identificar al solicitante.")
    return SimpleNamespace(rol=Rol(x_rol), id=x_usuario, email="test@example.com")


@pytest.fixture(autouse=True)
def sobrescribir_seguridad():
    app.dependency_overrides[get_current_user] = usuario_para_pruebas
    yield
    app.dependency_overrides.pop(get_current_user, None)
