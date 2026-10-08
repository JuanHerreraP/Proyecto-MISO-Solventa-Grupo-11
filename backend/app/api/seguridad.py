"""Rol del solicitante.

PROVISIONAL: mientras la HU19 (BPM-54) entrega el token de acceso, el rol se lee de la
cabecera `X-Rol`. Cuando exista el JWT, esta dependencia debe leer el rol del token validado
y la cabecera debe eliminarse. No desplegar a un ambiente expuesto con esta versión.
"""

from enum import Enum

from fastapi import Header, HTTPException, status


class Rol(str, Enum):
    ANALISTA_RIESGOS = "ANALISTA_RIESGOS"
    ASESOR_VENTAS = "ASESOR_VENTAS"
    CLIENTE = "CLIENTE"
    INGENIERO_INTEGRACIONES = "INGENIERO_INTEGRACIONES"
    SERVICIO_INTERNO = "SERVICIO_INTERNO"


def rol_actual(x_rol: str | None = Header(default=None)) -> Rol:
    if x_rol is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta identificar al solicitante.")
    try:
        return Rol(x_rol)
    except ValueError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rol no reconocido.") from None


def actor_actual(x_actor_id: str | None = Header(default=None)) -> str:
    """Identificador provisional del actor hasta que HU19 entregue el JWT."""

    if x_actor_id is None or not x_actor_id.strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta identificar al actor.")
    return x_actor_id.strip()
