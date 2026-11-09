"""Desembolso de indemnizaciones y cuenta de destino del cliente (HU15 / BPM-65).

La cuenta bancaria se tokeniza en la red de desembolsos: Solventa solo guarda el token y los
últimos cuatro dígitos, nunca el número completo (igual que HU13 con las tarjetas).
"""

import re
from decimal import Decimal
from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class TipoCuenta(str, Enum):
    AHORROS = "AHORROS"
    CORRIENTE = "CORRIENTE"


class MedioDesembolso(str, Enum):
    CUENTA_BANCARIA = "CUENTA_BANCARIA"
    CODIGO_RETIRO = "CODIGO_RETIRO"


class EstadoDesembolso(str, Enum):
    """Estado de la transferencia, como lo pide el criterio de aceptación."""

    PENDIENTE = "PENDIENTE"
    COMPLETADA = "COMPLETADA"
    FALLIDA = "FALLIDA"


BANCOS = {
    "1007": "Bancolombia",
    "1001": "Banco de Bogotá",
    "1051": "Davivienda",
    "1013": "BBVA Colombia",
    "1023": "Banco de Occidente",
    "1052": "Banco AV Villas",
    "1507": "Nequi",
}

_SOLO_DIGITOS = re.compile(r"^\d{6,20}$")


class SolicitudCuenta(BaseModel):
    """Lo que el cliente envía. El número solo viaja hacia la red para tokenizarse."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    codigo_banco: str = Field(min_length=4, max_length=4)
    tipo_cuenta: TipoCuenta
    numero_cuenta: str = Field(min_length=6, max_length=20)

    @field_validator("codigo_banco")
    @classmethod
    def banco_conocido(cls, valor: str) -> str:
        if valor not in BANCOS:
            raise ValueError("El banco no está habilitado para desembolsos.")
        return valor

    @field_validator("numero_cuenta")
    @classmethod
    def solo_digitos(cls, valor: str) -> str:
        valor = valor.replace(" ", "").replace("-", "")
        if not _SOLO_DIGITOS.match(valor):
            raise ValueError("El número de cuenta debe tener entre 6 y 20 dígitos.")
        return valor


class CuentaDesembolso(BaseModel):
    """Cuenta registrada por el cliente para recibir indemnizaciones."""

    model_config = ConfigDict(extra="forbid")

    cliente_id: str = Field(min_length=1, max_length=50)
    codigo_banco: str = Field(min_length=4, max_length=4)
    tipo_cuenta: TipoCuenta
    ultimos_digitos: str = Field(pattern=r"^\d{4}$")
    token_cuenta: str = Field(min_length=8, max_length=100)
    registrada_en: AwareDatetime
    actualizada_en: AwareDatetime

    @property
    def nombre_banco(self) -> str:
        return BANCOS.get(self.codigo_banco, self.codigo_banco)

    @property
    def enmascarada(self) -> str:
        return f"{self.nombre_banco} {self.tipo_cuenta.value.lower()} ****{self.ultimos_digitos}"


class Desembolso(BaseModel):
    """Orden de pago de la indemnización de un siniestro aprobado. Uno por siniestro."""

    model_config = ConfigDict(extra="forbid")

    desembolso_id: str = Field(min_length=1, max_length=50)
    siniestro_id: str = Field(min_length=1, max_length=50)
    poliza_id: str = Field(min_length=1, max_length=50)
    cliente_id: str = Field(min_length=1, max_length=50)
    monto: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    moneda: str = Field(pattern=r"^[A-Z]{3}$")
    medio: MedioDesembolso
    destino: str | None = Field(default=None, max_length=120)
    estado: EstadoDesembolso = EstadoDesembolso.PENDIENTE
    intento: int = Field(default=1, ge=1)
    referencia_transaccion: str | None = Field(default=None, max_length=100)
    codigo_retiro: str | None = Field(default=None, max_length=20)
    motivo_fallo: str | None = Field(default=None, max_length=200)
    creado_en: AwareDatetime
    actualizado_en: AwareDatetime
    completado_en: AwareDatetime | None = None

    @property
    def referencia_interna(self) -> str:
        """Estable mientras dure un intento: la red no paga dos veces la misma referencia."""
        return f"{self.desembolso_id}-{self.intento}"
