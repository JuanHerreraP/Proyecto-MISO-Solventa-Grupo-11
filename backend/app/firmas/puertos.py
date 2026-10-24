"""Puertos de la firma: el proveedor externo de firma electrónica y la persistencia.

Cambiar de proveedor (EC06) significa escribir otro adaptador de
`ProveedorFirmaElectronica`; el servicio de firmas no cambia.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.firmas.contrato import TitularContrato
from app.firmas.modelos import CanalOtp, ProcesoFirma


class ProveedorFirmaNoDisponible(Exception):
    """El proveedor no respondió o respondió con un contenido inválido."""


@dataclass(frozen=True)
class SolicitudEnvioOtp:
    referencia_proceso: str
    canal: CanalOtp
    destino: str
    codigo: str


@dataclass(frozen=True)
class SolicitudSello:
    referencia_proceso: str
    huella_documento: str
    firmante_id: str
    firmado_en: datetime
    ip_firmante: str | None


@dataclass(frozen=True)
class SelloFirma:
    referencia_proveedor: str
    sello: str


class ProveedorFirmaElectronica(Protocol):
    def enviar_otp(self, solicitud: SolicitudEnvioOtp) -> str:
        """Entrega el código al cliente y devuelve la referencia del envío."""
        ...

    def sellar(self, solicitud: SolicitudSello) -> SelloFirma:
        """Registra la firma ante el proveedor y devuelve su evidencia."""
        ...


class RepositorioFirmas(Protocol):
    def crear(self, proceso: ProcesoFirma) -> bool:
        """Inserta el proceso; devuelve False si la cotización ya tiene uno."""
        ...

    def guardar(self, proceso: ProcesoFirma) -> None: ...

    def obtener_por_cotizacion(self, cotizacion_id: str) -> ProcesoFirma | None: ...


class RepositorioTitulares(Protocol):
    def obtener(self, cliente_id: str) -> TitularContrato | None: ...
