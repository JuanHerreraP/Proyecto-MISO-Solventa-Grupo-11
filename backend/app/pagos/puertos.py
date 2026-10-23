"""Puertos del recaudo: la pasarela externa y la persistencia de pagos."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.pagos.modelos import EstadoPago, MetodoPago, Pago


class PasarelaNoDisponible(Exception):
    """La pasarela no respondió o respondió con un contenido inválido."""


@dataclass(frozen=True)
class SolicitudCobro:
    referencia_interna: str
    monto: Decimal
    moneda: str
    metodo: MetodoPago
    token_tarjeta: str | None = None
    codigo_banco: str | None = None
    url_retorno: str | None = None


@dataclass(frozen=True)
class ResultadoCobro:
    referencia_pasarela: str
    estado: EstadoPago
    url_redireccion: str | None = None
    motivo_rechazo: str | None = None


class PasarelaPagos(Protocol):
    def cobrar(self, solicitud: SolicitudCobro) -> ResultadoCobro:
        """Procesa el débito en línea o lanza `PasarelaNoDisponible`.

        La idempotencia frente a la pasarela se logra con `referencia_interna`, que es
        estable entre reintentos del mismo pago.
        """
        ...


class RepositorioPagos(Protocol):
    def guardar(self, pago: Pago) -> None: ...

    def crear(self, pago: Pago) -> bool:
        """Inserta el pago; devuelve False si (cliente, idempotency_key) ya existe."""
        ...

    def obtener(self, pago_id: str) -> Pago | None: ...

    def obtener_por_llave(self, cliente_id: str, idempotency_key: str) -> Pago | None: ...

    def obtener_por_referencia(self, referencia_pasarela: str) -> Pago | None: ...

    def obtener_aprobado_de_cotizacion(self, cotizacion_id: str) -> Pago | None: ...

    def listar_de_cliente(self, cliente_id: str) -> list[Pago]:
        """Pagos del cliente, del más reciente al más antiguo."""
