"""Rol del solicitante.

PROVISIONAL: mientras la HU19 (BPM-54) entrega el token de acceso, el rol se lee de la
cabecera `X-Rol`. Cuando exista el JWT, esta dependencia debe leer el rol del token validado
y la cabecera debe eliminarse. No desplegar a un ambiente expuesto con esta versión.
"""

from enum import Enum

from fastapi import Header, HTTPException, status


class Rol(str, Enum):
    ASESOR_VENTAS = "ASESOR_VENTAS"
    ANALISTA_RIESGOS = "ANALISTA_RIESGOS"
    OPERACIONES_SINIESTROS = "OPERACIONES_SINIESTROS"
    SOCIO_DISTRIBUCION = "SOCIO_DISTRIBUCION"
    CLIENTE = "CLIENTE"
    SERVICIO_INTERNO = "SERVICIO_INTERNO"


def rol_actual(x_rol: str | None = Header(default=None)) -> Rol:
    if x_rol is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta identificar al solicitante.")
    try:
        return Rol(x_rol)
    except ValueError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rol no reconocido.") from None
