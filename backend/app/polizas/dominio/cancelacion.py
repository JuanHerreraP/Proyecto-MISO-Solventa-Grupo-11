"""Reglas de la cancelación de la póliza (HU22 / BPM-35).

Cancelar es inmediato e irreversible: la póliza deja de estar vigente hoy. La prima de los
días de cobertura que el cliente ya no va a usar se convierte en un *saldo a favor estimado*,
calculado por días y sin penalización. El sistema solo lo registra como pendiente de
devolución; mover ese dinero queda fuera de esta historia.

Una póliza no se puede cancelar si no está vigente ni mientras tenga un siniestro en trámite.

Cálculo del saldo, por periodo pagado (una póliza renovada con anticipación tiene dos):

    saldo = prima x días sin usar / días del periodo

donde los días sin usar son los que quedan *después de hoy* (hoy cuenta como usado) y se
limitan al total del periodo: un periodo que aún no empieza se devuelve completo.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.polizas.dominio.modelos import EstadoPoliza, Poliza

PRECISION_MONEDA = Decimal("0.01")


class MotivoCancelacion(str, Enum):
    YA_NO_LA_NECESITO = "YA_NO_LA_NECESITO"
    PRECIO_ALTO = "PRECIO_ALTO"
    OTRA_ASEGURADORA = "OTRA_ASEGURADORA"
    COBERTURA_INSUFICIENTE = "COBERTURA_INSUFICIENTE"
    OTRO = "OTRO"


ETIQUETAS_MOTIVO: dict[MotivoCancelacion, str] = {
    MotivoCancelacion.YA_NO_LA_NECESITO: "Ya no la necesito",
    MotivoCancelacion.PRECIO_ALTO: "El precio es muy alto",
    MotivoCancelacion.OTRA_ASEGURADORA: "Contraté otro seguro",
    MotivoCancelacion.COBERTURA_INSUFICIENTE: "La cobertura no me sirve",
    MotivoCancelacion.OTRO: "Otro motivo",
}


class CodigoBloqueo(str, Enum):
    POLIZA_NO_VIGENTE = "POLIZA_NO_VIGENTE"
    SINIESTRO_EN_TRAMITE = "SINIESTRO_EN_TRAMITE"


class EstadoDevolucion(str, Enum):
    """La devolución solo se registra; gestionarla es una historia aparte."""

    PENDIENTE = "PENDIENTE"
    SIN_SALDO = "SIN_SALDO"


class Bloqueo(BaseModel):
    """Una razón por la que la póliza no se puede cancelar ahora."""

    model_config = ConfigDict(frozen=True)

    codigo: CodigoBloqueo
    mensaje: str
    siniestros: tuple[str, ...] = ()


class MotivoInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    codigo: MotivoCancelacion
    etiqueta: str


class PropuestaCancelacion(BaseModel):
    """Lo que el cliente ve antes de confirmar: condiciones, consecuencias y saldo."""

    model_config = ConfigDict(frozen=True)

    poliza_id: str
    numero_poliza: str
    cancelable: bool
    bloqueos: tuple[Bloqueo, ...]
    fecha_efecto: date
    dias_totales: int
    dias_no_transcurridos: int
    prima_total: Decimal
    saldo_estimado: Decimal
    moneda: str
    consecuencias: tuple[str, ...]
    motivos: tuple[MotivoInfo, ...]


class CancelacionNoPermitida(Exception):
    """La póliza no se puede cancelar; `bloqueos` dice por qué."""

    def __init__(self, bloqueos: Sequence[Bloqueo]):
        super().__init__(", ".join(b.codigo.value for b in bloqueos))
        self.bloqueos = tuple(bloqueos)


class ConfirmacionRequerida(Exception):
    """El cliente no confirmó de forma explícita la cancelación."""


class SolicitudCancelacion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    motivo: MotivoCancelacion
    detalle: str | None = Field(default=None, max_length=300)
    confirmo: bool = False


class Cancelacion(BaseModel):
    """Registro inmutable de una cancelación: quién, cuándo, por qué y el saldo calculado."""

    model_config = ConfigDict(extra="forbid")

    cancelacion_id: str = Field(min_length=1, max_length=60)
    poliza_id: str = Field(min_length=1, max_length=50)
    motivo: MotivoCancelacion
    detalle: str | None = Field(default=None, max_length=300)
    solicitado_por: str = Field(min_length=1, max_length=50)
    rol_solicitante: str = Field(min_length=1, max_length=40)
    clave_idempotencia: str | None = Field(default=None, max_length=100)
    huella_solicitud: str = Field(min_length=64, max_length=64)
    ip_solicitante: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=300)
    fecha_efecto: date
    dias_totales: int = Field(ge=0)
    dias_no_transcurridos: int = Field(ge=0)
    prima_total: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    saldo_estimado: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    moneda: str = Field(pattern=r"^[A-Z]{3}$")
    estado_devolucion: EstadoDevolucion
    creado_en: AwareDatetime


def cancelacion_id_de(poliza_id: str) -> str:
    """Una póliza se cancela una sola vez: el identificador sale de ella."""
    return f"CAN-{poliza_id}"


@dataclass(frozen=True)
class PeriodoPagado:
    inicio: date
    fin: date
    prima: Decimal

    @property
    def dias(self) -> int:
        return (self.fin - self.inicio).days + 1

    def dias_sin_usar(self, hoy: date) -> int:
        """Días de cobertura que quedan después de hoy, sin pasar del total del periodo."""
        return min(max((self.fin - hoy).days, 0), self.dias)


def periodo_de(poliza: Poliza) -> PeriodoPagado:
    return PeriodoPagado(poliza.fecha_inicio, poliza.fecha_fin, poliza.prima_total)


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(PRECISION_MONEDA, rounding=ROUND_HALF_UP)


def calcular_saldo(periodos: Sequence[PeriodoPagado], hoy: date) -> tuple[Decimal, int, int]:
    """Devuelve (saldo a favor, días totales, días sin usar) sumando todos los periodos."""
    saldo = Decimal("0")
    totales = 0
    sin_usar = 0
    for periodo in periodos:
        dias_sin_usar = periodo.dias_sin_usar(hoy)
        saldo += periodo.prima * Decimal(dias_sin_usar) / Decimal(periodo.dias)
        totales += periodo.dias
        sin_usar += dias_sin_usar
    return _redondear(saldo), totales, sin_usar


def _bloqueo_por_estado(estado: EstadoPoliza) -> Bloqueo:
    if estado is EstadoPoliza.CANCELADA:
        mensaje = "La póliza ya está cancelada."
    else:
        mensaje = "La póliza ya venció; no hay nada que cancelar."
    return Bloqueo(codigo=CodigoBloqueo.POLIZA_NO_VIGENTE, mensaje=mensaje)


def _bloqueo_por_siniestros(siniestros: Sequence[str]) -> Bloqueo:
    cuantos = "un siniestro" if len(siniestros) == 1 else f"{len(siniestros)} siniestros"
    resolverse = "se resuelva" if len(siniestros) == 1 else "se resuelvan"
    return Bloqueo(
        codigo=CodigoBloqueo.SINIESTRO_EN_TRAMITE,
        mensaje=(
            f"Tienes {cuantos} en trámite (en evaluación o con la indemnización sin desembolsar). "
            f"Podrás cancelar la póliza cuando {resolverse}."
        ),
        siniestros=tuple(siniestros),
    )


def _consecuencias(saldo: Decimal) -> tuple[str, ...]:
    if saldo > 0:
        saldo_texto = (
            "Se calcula un saldo estimado a favor por los días de cobertura que no vas a usar. "
            "La devolución queda pendiente de gestión."
        )
    else:
        saldo_texto = "No hay saldo a favor porque ya usaste todo el periodo pagado."
    return (
        "Tu cobertura termina hoy: después no podrás reportar siniestros con esta póliza.",
        "La cancelación es definitiva y no se puede deshacer.",
        "La póliza dejará de aparecer entre tus coberturas activas; su certificado se conserva "
        "como constancia.",
        saldo_texto,
    )


def proponer_cancelacion(
    poliza: Poliza,
    hoy: date,
    siniestros_en_tramite: Sequence[str] = (),
    periodos: Sequence[PeriodoPagado] | None = None,
) -> PropuestaCancelacion:
    """Evalúa si la póliza se puede cancelar hoy y calcula el saldo, sin guardar nada."""

    bloqueos: list[Bloqueo] = []
    estado = poliza.estado_en(hoy)
    if estado is not EstadoPoliza.VIGENTE:
        bloqueos.append(_bloqueo_por_estado(estado))
    elif siniestros_en_tramite:
        bloqueos.append(_bloqueo_por_siniestros(siniestros_en_tramite))

    if estado is EstadoPoliza.VIGENTE:
        saldo, dias_totales, dias_sin_usar = calcular_saldo(periodos or [periodo_de(poliza)], hoy)
    else:
        saldo, dias_totales, dias_sin_usar = Decimal("0.00"), 0, 0

    return PropuestaCancelacion(
        poliza_id=poliza.poliza_id,
        numero_poliza=poliza.numero_poliza,
        cancelable=not bloqueos,
        bloqueos=tuple(bloqueos),
        fecha_efecto=hoy,
        dias_totales=dias_totales,
        dias_no_transcurridos=dias_sin_usar,
        prima_total=poliza.prima_total,
        saldo_estimado=saldo,
        moneda=poliza.moneda,
        consecuencias=_consecuencias(saldo),
        motivos=tuple(
            MotivoInfo(codigo=motivo, etiqueta=ETIQUETAS_MOTIVO[motivo])
            for motivo in MotivoCancelacion
        ),
    )
