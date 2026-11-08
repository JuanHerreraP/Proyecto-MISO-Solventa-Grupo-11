"""Puertos del desembolso: la red de pagos externa y la persistencia (HU15)."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.desembolsos.modelos import (
    CuentaDesembolso,
    Desembolso,
    EstadoDesembolso,
    TipoCuenta,
)


class RedNoDisponible(Exception):
    """La red de desembolsos no respondió: el desembolso queda pendiente para reintentar."""


@dataclass(frozen=True)
class Transferencia:
    referencia_interna: str
    monto: Decimal
    moneda: str
    token_cuenta: str


@dataclass(frozen=True)
class OrdenRetiro:
    referencia_interna: str
    monto: Decimal
    moneda: str


@dataclass(frozen=True)
class ResultadoDesembolso:
    referencia_transaccion: str
    estado: EstadoDesembolso
    codigo_retiro: str | None = None
    motivo_fallo: str | None = None


class RedDesembolsos(Protocol):
    """Pasarela de pagos o red de desembolsos autorizada. Sustituible sin tocar el servicio."""

    def tokenizar_cuenta(self, codigo_banco: str, tipo: TipoCuenta, numero: str) -> str: ...

    def transferir(self, transferencia: Transferencia) -> ResultadoDesembolso:
        """Idempotente por `referencia_interna`; lanza `RedNoDisponible` si no responde."""
        ...

    def emitir_codigo_retiro(self, orden: OrdenRetiro) -> ResultadoDesembolso:
        """Idempotente por `referencia_interna`; lanza `RedNoDisponible` si no responde."""
        ...


class RepositorioDesembolsos(Protocol):
    def crear(self, desembolso: Desembolso) -> bool:
        """Inserta; devuelve False si el siniestro ya tiene desembolso."""
        ...

    def guardar(self, desembolso: Desembolso) -> None: ...

    def obtener_por_siniestro(self, siniestro_id: str) -> Desembolso | None: ...

    def listar_por_cliente(self, cliente_id: str) -> list[Desembolso]: ...


class RepositorioCuentas(Protocol):
    def guardar(self, cuenta: CuentaDesembolso) -> None: ...

    def obtener(self, cliente_id: str) -> CuentaDesembolso | None: ...
