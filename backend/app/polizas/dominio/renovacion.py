"""Reglas de la renovación de la póliza (HU22 / BPM-35).

Renovar es continuar la cobertura: la nueva vigencia empieza el día siguiente al fin de la actual
y la póliza conserva su número. La prima se recalcula con la tarifa y el perfil de riesgo
vigentes, más las coberturas opcionales que el cliente agregó con endosos. El cliente la paga
como cualquier cotización; solo cuando el pago se aprueba se actualiza la póliza.

- Renuevan los ramos de vida, protección de dispositivos y paramétrico.
- Se puede renovar desde 30 días antes del vencimiento. Una póliza vencida o cancelada no se
  renueva: hay que contratar una nueva.
- Si el pago no se aprueba (o la cotización vence), la póliza queda exactamente como estaba.
"""

import calendar
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.polizas.dominio.endosos import dias_de_vigencia, prima_de_opcionales
from app.polizas.dominio.modelos import EstadoPoliza, Poliza, RamoPoliza

RAMOS_RENOVABLES = frozenset(
    {RamoPoliza.VIDA, RamoPoliza.PROTECCION_DISPOSITIVOS, RamoPoliza.PARAMETRICO}
)
VENTANA_RENOVACION_DIAS = 30


class CodigoBloqueoRenovacion(str, Enum):
    POLIZA_NO_VIGENTE = "POLIZA_NO_VIGENTE"
    RAMO_NO_RENOVABLE = "RAMO_NO_RENOVABLE"
    YA_RENOVADA = "YA_RENOVADA"
    FUERA_DE_VENTANA = "FUERA_DE_VENTANA"
    SIN_DATOS_DE_RIESGO = "SIN_DATOS_DE_RIESGO"
    RIESGO_NO_ASEGURABLE = "RIESGO_NO_ASEGURABLE"


class EstadoRenovacion(str, Enum):
    PENDIENTE_PAGO = "PENDIENTE_PAGO"
    APLICADA = "APLICADA"
    # No se guarda: se deriva de la vigencia de la cotización de la renovación.
    VENCIDA = "VENCIDA"
    # Se pagó, pero la póliza ya no se podía renovar (p. ej. se canceló mientras tanto).
    NO_APLICADA = "NO_APLICADA"


class BloqueoRenovacion(BaseModel):
    """Una razón por la que la póliza no se puede renovar ahora."""

    model_config = ConfigDict(frozen=True)

    codigo: CodigoBloqueoRenovacion
    mensaje: str


class Vigencia(BaseModel):
    model_config = ConfigDict(frozen=True)

    inicio: date
    fin: date


class CoberturaRenovada(BaseModel):
    model_config = ConfigDict(frozen=True)

    codigo: str
    nombre: str
    suma_asegurada: Decimal
    principal: bool
    prima: Decimal


class PropuestaRenovacion(BaseModel):
    """Lo que el cliente ve antes de confirmar: nueva vigencia, coberturas y prima."""

    model_config = ConfigDict(frozen=True)

    poliza_id: str
    numero_poliza: str
    renovable: bool
    bloqueos: tuple[BloqueoRenovacion, ...]
    vigencia_actual: Vigencia
    renovable_desde: date
    nueva_vigencia: Vigencia | None = None
    coberturas: tuple[CoberturaRenovada, ...] = ()
    prima_actual: Decimal
    prima_principal: Decimal | None = None
    prima_opcionales: Decimal | None = None
    prima_nueva: Decimal | None = None
    moneda: str
    personalizada: bool = False
    condiciones: tuple[str, ...] = ()


class RenovacionNoPermitida(Exception):
    """La póliza no se puede renovar; `bloqueos` dice por qué."""

    def __init__(self, bloqueos: Sequence[BloqueoRenovacion]):
        super().__init__(", ".join(b.codigo.value for b in bloqueos))
        self.bloqueos = tuple(bloqueos)


class RenovacionNoEncontrada(Exception):
    pass


class Renovacion(BaseModel):
    """Renovación de una póliza: su cotización, el periodo anterior y el nuevo."""

    model_config = ConfigDict(extra="forbid")

    renovacion_id: str = Field(min_length=1, max_length=70)
    poliza_id: str = Field(min_length=1, max_length=50)
    cotizacion_id: str = Field(min_length=1, max_length=50)
    estado: EstadoRenovacion = EstadoRenovacion.PENDIENTE_PAGO
    anterior_inicio: date
    anterior_fin: date
    anterior_prima: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    nuevo_inicio: date
    nuevo_fin: date
    prima_principal: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    prima_opcionales: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    prima_total: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    moneda: str = Field(pattern=r"^[A-Z]{3}$")
    vigente_hasta: AwareDatetime
    pago_id: str | None = Field(default=None, max_length=50)
    solicitado_por: str = Field(min_length=1, max_length=50)
    rol_solicitante: str = Field(min_length=1, max_length=40)
    clave_idempotencia: str | None = Field(default=None, max_length=100)
    ip_solicitante: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=300)
    creado_en: AwareDatetime
    aplicada_en: AwareDatetime | None = None
    motivo_no_aplicada: str | None = Field(default=None, max_length=200)

    def estado_en(self, ahora: datetime) -> EstadoRenovacion:
        if self.estado is EstadoRenovacion.PENDIENTE_PAGO and ahora >= self.vigente_hasta:
            return EstadoRenovacion.VENCIDA
        return self.estado

    def pendiente_en(self, ahora: datetime) -> bool:
        return self.estado_en(ahora) is EstadoRenovacion.PENDIENTE_PAGO


def renovacion_id_de(poliza_id: str, nuevo_inicio: date) -> str:
    """Una póliza se renueva una vez por periodo: el identificador sale de ambos."""
    return f"REN-{poliza_id}-{nuevo_inicio:%Y%m%d}"


# --- Reglas ------------------------------------------------------------------------------


def renovable_desde(poliza: Poliza) -> date:
    return poliza.fecha_fin - timedelta(days=VENTANA_RENOVACION_DIAS)


def evaluar_bloqueos(poliza: Poliza, hoy: date) -> list[BloqueoRenovacion]:
    """Bloqueos que dependen solo de la póliza y de la fecha."""
    estado = poliza.estado_en(hoy)
    if estado is not EstadoPoliza.VIGENTE:
        mensaje = (
            "La póliza está cancelada y no se puede renovar."
            if estado is EstadoPoliza.CANCELADA
            else "La póliza ya venció. Contrata una nueva para volver a estar asegurado."
        )
        return [
            BloqueoRenovacion(codigo=CodigoBloqueoRenovacion.POLIZA_NO_VIGENTE, mensaje=mensaje)
        ]
    if poliza.ramo not in RAMOS_RENOVABLES:
        return [
            BloqueoRenovacion(
                codigo=CodigoBloqueoRenovacion.RAMO_NO_RENOVABLE,
                mensaje=(
                    f"{poliza.nombre_ramo} no se renueva: se contrata de nuevo cuando lo necesites."
                ),
            )
        ]
    if poliza.fecha_inicio > hoy:
        return [
            BloqueoRenovacion(
                codigo=CodigoBloqueoRenovacion.YA_RENOVADA,
                mensaje=(
                    "Tu póliza ya está renovada: la nueva vigencia empieza el "
                    f"{poliza.fecha_inicio:%d/%m/%Y}."
                ),
            )
        ]
    if hoy < renovable_desde(poliza):
        return [
            BloqueoRenovacion(
                codigo=CodigoBloqueoRenovacion.FUERA_DE_VENTANA,
                mensaje=(
                    f"Podrás renovar desde el {renovable_desde(poliza):%d/%m/%Y}, "
                    f"{VENTANA_RENOVACION_DIAS} días antes de que venza."
                ),
            )
        ]
    return []


def _sumar_meses(inicio: date, meses: int) -> date:
    indice = inicio.year * 12 + (inicio.month - 1) + meses
    anio, mes = divmod(indice, 12)
    dia = min(inicio.day, calendar.monthrange(anio, mes + 1)[1])
    return date(anio, mes + 1, dia)


def _meses_de_cobertura(datos_riesgo: dict[str, object]) -> int | None:
    for campo in ("meses_cobertura", "plazo_meses"):
        valor = datos_riesgo.get(campo)
        if isinstance(valor, int) and not isinstance(valor, bool) and 0 < valor <= 1200:
            return valor
    return None


def nueva_vigencia(poliza: Poliza, datos_riesgo: dict[str, object]) -> Vigencia:
    """Continúa la cobertura: empieza al día siguiente y dura lo mismo que la anterior.

    Si el riesgo se contrató por meses, se renueva por esos meses; si no, por los mismos días.
    """
    inicio = poliza.fecha_fin + timedelta(days=1)
    meses = _meses_de_cobertura(datos_riesgo)
    if meses is not None:
        fin = _sumar_meses(inicio, meses) - timedelta(days=1)
    else:
        fin = inicio + timedelta(days=dias_de_vigencia(poliza) - 1)
    return Vigencia(inicio=inicio, fin=fin)


def datos_de_renovacion(datos_riesgo: dict[str, object], vigencia: Vigencia) -> dict[str, object]:
    """Datos del riesgo para cotizar el nuevo periodo (las fechas del periodo se actualizan)."""
    datos = dict(datos_riesgo)
    if "fecha_inicio" in datos and "fecha_fin" in datos:
        datos["fecha_inicio"] = vigencia.inicio.isoformat()
        datos["fecha_fin"] = vigencia.fin.isoformat()
    return datos


def coberturas_renovadas(
    poliza: Poliza, prima_principal: Decimal, dias: int
) -> tuple[CoberturaRenovada, ...]:
    principal = poliza.cobertura_principal
    resultado = [
        CoberturaRenovada(
            codigo=principal.codigo,
            nombre=principal.nombre,
            suma_asegurada=principal.suma_asegurada,
            principal=True,
            prima=prima_principal,
        )
    ]
    for cobertura in poliza.coberturas_opcionales:
        resultado.append(
            CoberturaRenovada(
                codigo=cobertura.codigo,
                nombre=cobertura.nombre,
                suma_asegurada=cobertura.suma_asegurada,
                principal=False,
                prima=prima_de_opcionales(poliza.ramo, [cobertura], dias),
            )
        )
    return tuple(resultado)


def _condiciones(vigencia: Vigencia) -> tuple[str, ...]:
    return (
        f"La renovación empieza el {vigencia.inicio:%d/%m/%Y}, cuando termina tu vigencia actual.",
        "La póliza conserva su número; el pago aprobado la actualiza con la nueva vigencia.",
        "La prima se recalcula con la tarifa y tu perfil de riesgo vigentes.",
        "Si el pago no se aprueba, tu póliza queda como está.",
    )


def sin_precio(poliza: Poliza, bloqueos: Sequence[BloqueoRenovacion]) -> PropuestaRenovacion:
    """Propuesta de una póliza que no se puede renovar (o cuyo precio no se pudo calcular)."""
    return PropuestaRenovacion(
        poliza_id=poliza.poliza_id,
        numero_poliza=poliza.numero_poliza,
        renovable=False,
        bloqueos=tuple(bloqueos),
        vigencia_actual=Vigencia(inicio=poliza.fecha_inicio, fin=poliza.fecha_fin),
        renovable_desde=renovable_desde(poliza),
        prima_actual=poliza.prima_total,
        moneda=poliza.moneda,
    )


def proponer_renovacion(
    poliza: Poliza,
    vigencia: Vigencia,
    prima_principal: Decimal,
    personalizada: bool,
) -> PropuestaRenovacion:
    """Propuesta con precio: se llama solo si la póliza se puede renovar."""
    dias = (vigencia.fin - vigencia.inicio).days + 1
    coberturas = coberturas_renovadas(poliza, prima_principal, dias)
    opcionales = sum((c.prima for c in coberturas if not c.principal), Decimal("0.00"))
    return PropuestaRenovacion(
        poliza_id=poliza.poliza_id,
        numero_poliza=poliza.numero_poliza,
        renovable=True,
        bloqueos=(),
        vigencia_actual=Vigencia(inicio=poliza.fecha_inicio, fin=poliza.fecha_fin),
        renovable_desde=renovable_desde(poliza),
        nueva_vigencia=vigencia,
        coberturas=coberturas,
        prima_actual=poliza.prima_total,
        prima_principal=prima_principal,
        prima_opcionales=opcionales,
        prima_nueva=prima_principal + opcionales,
        moneda=poliza.moneda,
        personalizada=personalizada,
        condiciones=_condiciones(vigencia),
    )


def poliza_renovada(poliza: Poliza, renovacion: Renovacion) -> Poliza:
    """La póliza con la nueva vigencia y la prima cobrada. Conserva número, coberturas y firma."""
    return poliza.model_copy(
        update={
            "fecha_inicio": renovacion.nuevo_inicio,
            "fecha_fin": renovacion.nuevo_fin,
            "prima_total": renovacion.prima_total,
        }
    )
