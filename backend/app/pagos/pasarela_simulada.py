"""Pasarela simulada para desarrollo y pruebas (sustituible por el proveedor real).

Comportamiento determinista según el token, para poder probar los tres desenlaces:
- `tok_rechazado*`  -> RECHAZADO
- `tok_caido*`      -> PasarelaNoDisponible
- cualquier otro    -> APROBADO
- PSE               -> PENDIENTE con URL de redirección; la confirmación llega por webhook.
"""

import hashlib

from app.pagos.modelos import EstadoPago, MetodoPago
from app.pagos.puertos import (
    PasarelaNoDisponible,
    ResultadoCobro,
    SolicitudCobro,
)


class PasarelaSimulada:
    def __init__(self, url_base: str = "https://pasarela.simulada.local"):
        self._url_base = url_base

    def cobrar(self, solicitud: SolicitudCobro) -> ResultadoCobro:
        referencia = "PSP-" + hashlib.sha256(solicitud.referencia_interna.encode()).hexdigest()[:16]

        if solicitud.metodo is MetodoPago.PSE:
            return ResultadoCobro(
                referencia_pasarela=referencia,
                estado=EstadoPago.PENDIENTE,
                url_redireccion=f"{self._url_base}/pse/{referencia}",
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
