"""Pasarela simulada para desarrollo (sustituible por el proveedor real).

Comportamiento determinista según el token, para poder probar los tres desenlaces:
- `tok_rechazado*`  -> RECHAZADO
- `tok_caido*`      -> PasarelaNoDisponible
- cualquier otro    -> APROBADO
- PSE               -> PENDIENTE con URL de redirección a un portal PSE simulado de la
                       propia app; la confirmación llega por webhook cuando el cliente paga.
"""

import hashlib
import os
from urllib.parse import quote

from app.pagos.modelos import EstadoPago, MetodoPago
from app.pagos.puertos import (
    PasarelaNoDisponible,
    ResultadoCobro,
    SolicitudCobro,
)

# Ruta del portal PSE simulado que sirve el propio backend (ver app/api/pse_simulado.py).
RUTA_PORTAL_PSE = "/api/v1/pagos/pse-simulado"


def _url_base_app() -> str:
    """Base pública de la app; en local el backend expone el portal PSE simulado."""
    return os.getenv("SOLVENTA_URL_PUBLICA", "http://localhost:8000").rstrip("/")


class PasarelaSimulada:
    def __init__(self, url_base: str | None = None):
        self._url_base = (url_base or _url_base_app()).rstrip("/")

    def cobrar(self, solicitud: SolicitudCobro) -> ResultadoCobro:
        referencia = "PSP-" + hashlib.sha256(solicitud.referencia_interna.encode()).hexdigest()[:16]

        if solicitud.metodo is MetodoPago.PSE:
            destino = f"{self._url_base}{RUTA_PORTAL_PSE}/{referencia}"
            if solicitud.url_retorno:
                destino += f"?url_retorno={quote(solicitud.url_retorno, safe='')}"
            return ResultadoCobro(
                referencia_pasarela=referencia,
                estado=EstadoPago.PENDIENTE,
                url_redireccion=destino,
            )

        token = solicitud.token_tarjeta or ""
        if token.startswith("tok_caido"):
            raise PasarelaNoDisponible("tiempo de espera agotado")
        if token.startswith("tok_rechazado"):
            return ResultadoCobro(
                referencia_pasarela=referencia,
                estado=EstadoPago.RECHAZADO,
                motivo_rechazo="FONDOS_INSUFICIENTES",
            )
        return ResultadoCobro(referencia_pasarela=referencia, estado=EstadoPago.APROBADO)
