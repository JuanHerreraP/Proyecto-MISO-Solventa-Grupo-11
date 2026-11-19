"""Reglas de la renovación automática de la póliza (HU17 / BPM-69).

La renovación automática reutiliza la renovación de HU22 (misma propuesta, misma cotización de
renovación y mismo pago); lo que agrega es quién la dispara y cuándo:

- La renovación automática está activa por defecto: el cliente puede desactivarla y volver a
  activarla. Para cobrar sin intervención necesita una tarjeta tokenizada registrada; nunca se
  guarda el número de la tarjeta, solo el token de la pasarela y sus últimos cuatro dígitos.
- 30 días antes del vencimiento se envía un correo de preaviso con la prima de la renovación
  recalculada con la tarifa y el perfil de riesgo vigentes (ajuste actuarial).
- El día del vencimiento, si sigue activa, se crea la renovación y se cobra con la tarjeta
  registrada. Con el pago aprobado la póliza toma la nueva vigencia, se emite el documento
  contractual del nuevo periodo y se envía al cliente.
- Cada periodo de una póliza tiene un único ciclo de renovación automática. El ciclo deja
  constancia de lo que se hizo (preaviso, cobro, documento y envío) y hace que ejecutar la tarea
  dos veces el mismo día no duplique correos ni cobros.
"""

import hashlib
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.pagos.modelos import validar_token_pago
from app.polizas.dominio.modelos import EstadoPoliza, Poliza
from app.polizas.dominio.renovacion import RAMOS_RENOVABLES, VENTANA_RENOVACION_DIAS

DIAS_PREAVISO = VENTANA_RENOVACION_DIAS
ACTOR_SISTEMA = "SISTEMA-RENOVACION-AUTOMATICA"

_ULTIMOS_DIGITOS = re.compile(r"^\d{4}$")


class EstadoCicloRenovacion(str, Enum):
    # Se envió el preaviso; falta llegar a la fecha de vencimiento.
    PREAVISADA = "PREAVISADA"
    # El cliente desactivó la renovación automática antes del vencimiento.
    DESACTIVADA = "DESACTIVADA"
    # Activa, pero sin tarjeta registrada: el cliente debe renovar manualmente (HU22).
    SIN_MEDIO_DE_PAGO = "SIN_MEDIO_DE_PAGO"
    # La pasarela no respondió: el pago queda pendiente hasta su confirmación.
    COBRO_PENDIENTE = "COBRO_PENDIENTE"
    # La pasarela rechazó el cobro. Se reintenta si el cliente registra otra tarjeta.
    COBRO_RECHAZADO = "COBRO_RECHAZADO"
    # La póliza ya no se podía renovar (riesgo no asegurable, sin datos de riesgo, ...).
    NO_RENOVABLE = "NO_RENOVABLE"
    # Se cobró, pero la renovación no se aplicó (p. ej. la póliza se canceló mientras tanto).
    NO_APLICADA = "NO_APLICADA"
    # La cotización de la renovación venció sin un pago aprobado.
    NO_PAGADA = "NO_PAGADA"
    # Cobrada y aplicada: la póliza tiene la nueva vigencia.
    RENOVADA = "RENOVADA"


ESTADOS_FINALES = frozenset(
    {
        EstadoCicloRenovacion.RENOVADA,
        EstadoCicloRenovacion.NO_APLICADA,
        EstadoCicloRenovacion.NO_RENOVABLE,
        EstadoCicloRenovacion.NO_PAGADA,
    }
)

# Ciclos a los que la tarea les sigue la pista aunque la póliza ya no esté en la ventana:
# esperan la confirmación del pago, una tarjeta nueva o el envío del contrato.
ESTADOS_CON_SEGUIMIENTO = frozenset(
    {
        EstadoCicloRenovacion.COBRO_PENDIENTE,
        EstadoCicloRenovacion.SIN_MEDIO_DE_PAGO,
        EstadoCicloRenovacion.COBRO_RECHAZADO,
        EstadoCicloRenovacion.RENOVADA,
    }
)


class MedioPagoRegistrado(BaseModel):
    """Tarjeta tokenizada con la que se cobran las renovaciones automáticas."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    token_tarjeta: str = Field(min_length=8, max_length=200)
    ultimos_digitos: str | None = None

    _sin_pan = field_validator("token_tarjeta")(validar_token_pago)

    @field_validator("ultimos_digitos")
    @classmethod
    def _cuatro_digitos(cls, valor: str | None) -> str | None:
        if valor is not None and not _ULTIMOS_DIGITOS.match(valor):
            raise ValueError("Los últimos dígitos deben ser exactamente cuatro números.")
        return valor

    @property
    def huella(self) -> str:
        return huella_de_token(self.token_tarjeta)


class PreferenciaRenovacionAutomatica(BaseModel):
    """Lo que decidió el cliente sobre la renovación automática de una póliza."""

    model_config = ConfigDict(extra="forbid")

    poliza_id: str = Field(min_length=1, max_length=50)
    activa: bool = True
    medio_pago: MedioPagoRegistrado | None = None
    actualizado_por: str | None = Field(default=None, max_length=50)
    actualizado_en: AwareDatetime | None = None


class CicloRenovacionAutomatica(BaseModel):
    """Lo que hizo la renovación automática con un periodo de la póliza."""

    model_config = ConfigDict(extra="forbid")

    ciclo_id: str = Field(min_length=1, max_length=80)
    poliza_id: str = Field(min_length=1, max_length=50)
    vence_el: date
    estado: EstadoCicloRenovacion = EstadoCicloRenovacion.PREAVISADA
    preaviso_enviado_en: AwareDatetime | None = None
    prima_avisada: Decimal | None = Field(default=None, max_digits=18, decimal_places=2)
    moneda: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    renovacion_id: str | None = Field(default=None, max_length=70)
    pago_id: str | None = Field(default=None, max_length=50)
    huella_medio_cobrado: str | None = Field(default=None, min_length=64, max_length=64)
    intentos_cobro: int = Field(default=0, ge=0)
    motivo: str | None = Field(default=None, max_length=200)
    clave_documento: str | None = Field(default=None, max_length=200)
    huella_documento: str | None = Field(default=None, min_length=64, max_length=64)
    tamano_documento: int | None = Field(default=None, gt=0)
    contrato_enviado_en: AwareDatetime | None = None
    aviso_enviado_en: AwareDatetime | None = None
    creado_en: AwareDatetime
    actualizado_en: AwareDatetime

    @property
    def documento_pendiente(self) -> bool:
        return self.estado is EstadoCicloRenovacion.RENOVADA and (
            self.huella_documento is None or self.contrato_enviado_en is None
        )

    @property
    def requiere_seguimiento(self) -> bool:
        if self.estado is EstadoCicloRenovacion.RENOVADA:
            return self.documento_pendiente
        return self.estado in ESTADOS_CON_SEGUIMIENTO and self.renovacion_id is not None


class ResultadoEjecucion(BaseModel):
    """Resumen de una ejecución de la tarea, para operaciones y para el log."""

    fecha: date
    revisadas: int = 0
    preavisos: int = 0
    renovadas: int = 0
    contratos_enviados: int = 0
    sin_medio_de_pago: int = 0
    desactivadas: int = 0
    rechazadas: int = 0
    pendientes: int = 0
    no_renovables: int = 0
    errores: int = 0


def huella_de_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def ciclo_id_de(poliza_id: str, vence_el: date) -> str:
    """Un ciclo por periodo: se identifica por la póliza y el fin del periodo que se renueva."""
    return f"AUT-{poliza_id}-{vence_el:%Y%m%d}"


def llave_cobro(cotizacion_id: str, medio: MedioPagoRegistrado) -> str:
    """Llave de idempotencia del cobro: la misma cotización con la misma tarjeta se cobra una vez.

    Si el cliente registra otra tarjeta tras un rechazo, la llave cambia y se puede reintentar.
    """
    base = f"{cotizacion_id}|{medio.huella}"
    return "AUT-" + hashlib.sha256(base.encode()).hexdigest()[:48]


def preaviso_desde(poliza: Poliza) -> date:
    return poliza.fecha_fin - timedelta(days=DIAS_PREAVISO)


def candidata(poliza: Poliza, hoy: date) -> bool:
    """La póliza está vigente, se renueva y entró en la ventana de preaviso."""
    return (
        poliza.estado_en(hoy) is EstadoPoliza.VIGENTE
        and poliza.ramo in RAMOS_RENOVABLES
        and poliza.fecha_inicio <= hoy
        and preaviso_desde(poliza) <= hoy <= poliza.fecha_fin
    )


def toca_cobrar(poliza: Poliza, hoy: date) -> bool:
    """La renovación se cobra el último día de la vigencia actual."""
    return hoy >= poliza.fecha_fin


def nuevo_ciclo(poliza: Poliza, ahora: datetime) -> CicloRenovacionAutomatica:
    return CicloRenovacionAutomatica(
        ciclo_id=ciclo_id_de(poliza.poliza_id, poliza.fecha_fin),
        poliza_id=poliza.poliza_id,
        vence_el=poliza.fecha_fin,
        creado_en=ahora,
        actualizado_en=ahora,
    )
