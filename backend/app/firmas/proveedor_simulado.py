"""Proveedor de firma simulado para desarrollo y pruebas (sustituible por el real).

No envía SMS ni correos: deja el código en el log del backend para poder completar el
flujo en local. Nunca usarlo en un ambiente con clientes reales.
"""

import hashlib
import hmac
import logging

from app.firmas.puertos import (
    ProveedorFirmaNoDisponible,
    SelloFirma,
    SolicitudEnvioOtp,
    SolicitudSello,
)

logger = logging.getLogger(__name__)

_LLAVE_SELLO = b"solventa-firma-simulada"


class ProveedorFirmaSimulado:
    def __init__(self, disponible: bool = True):
        self.disponible = disponible
        self.ultimo_codigo: str | None = None
        self.envios = 0
        self.sellos = 0

    def enviar_otp(self, solicitud: SolicitudEnvioOtp) -> str:
        if not self.disponible:
            raise ProveedorFirmaNoDisponible("simulador apagado")
        self.envios += 1
        self.ultimo_codigo = solicitud.codigo
        logger.warning(
            "[FIRMA SIMULADA] OTP %s para %s por %s (proceso %s)",
            solicitud.codigo,
            solicitud.destino,
            solicitud.canal.value,
            solicitud.referencia_proceso,
        )
        return f"ENV-{solicitud.referencia_proceso[-8:]}-{self.envios}"

    def sellar(self, solicitud: SolicitudSello) -> SelloFirma:
        if not self.disponible:
            raise ProveedorFirmaNoDisponible("simulador apagado")
        self.sellos += 1
        material = (
            f"{solicitud.referencia_proceso}|{solicitud.huella_documento}|"
            f"{solicitud.firmante_id}|{solicitud.firmado_en.isoformat()}"
        ).encode()
        sello = hmac.new(_LLAVE_SELLO, material, hashlib.sha256).hexdigest()
        referencia = "SIM-" + hashlib.sha256(solicitud.referencia_proceso.encode()).hexdigest()[:16]
        return SelloFirma(referencia_proveedor=referencia, sello=sello)
