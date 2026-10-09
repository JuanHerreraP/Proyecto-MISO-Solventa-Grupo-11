import pytest
from fastapi import Header, HTTPException, status

from app.api.seguridad import Rol, rol_actual
from app.main import app


def rol_actual_para_pruebas(
    x_rol: str | None = Header(default=None),
) -> Rol:
    if x_rol is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta identificar al solicitante.",
        )

    try:
        return Rol(x_rol)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rol no reconocido.",
        ) from err


@pytest.fixture(autouse=True)
def sobrescribir_seguridad():
    app.dependency_overrides[rol_actual] = rol_actual_para_pruebas

    yield

    app.dependency_overrides.pop(rol_actual, None)
