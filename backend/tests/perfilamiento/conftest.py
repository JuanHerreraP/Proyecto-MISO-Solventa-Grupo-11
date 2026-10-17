from types import SimpleNamespace

import pytest
from fastapi import Header, HTTPException, status

from app.api.seguridad import Rol, get_current_user
from app.main import app


def rol_actual_para_pruebas(
    x_rol: str | None = Header(default=None),
    x_usuario: str = Header(default="CLI-001"),
) -> Rol:
    if x_rol is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta identificar al solicitante.",
        )

    try:
        return SimpleNamespace(rol=Rol(x_rol), id=x_usuario, email="test@example.com")
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rol no reconocido.",
        ) from err


@pytest.fixture(autouse=True)
def sobrescribir_seguridad():
    app.dependency_overrides[get_current_user] = rol_actual_para_pruebas

    yield

    app.dependency_overrides.pop(get_current_user, None)
