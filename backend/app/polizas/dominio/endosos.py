"""Reglas del endoso: beneficiarios, coberturas opcionales y ajuste pro-rata (HU16 / BPM-68).

Un endoso parte de una solicitud con el estado deseado (la lista completa de beneficiarios o
de coberturas opcionales; lo que no se envía no cambia) y produce una propuesta: qué cambia,
cuánto vale el ajuste de prima por el periodo que falta y cuál queda siendo la prima total.

Tarifa de las coberturas opcionales: suma asegurada x tasa mensual x meses de vigencia, con
el mes de 30 días. El ajuste es la diferencia entre la tarifa nueva y la anterior, en la
proporción de días que le faltan a la póliza (incluido el día del cambio). Un ajuste positivo
es un cobro; uno negativo, una devolución de prima no devengada.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.polizas.dominio.modelos import (
    Beneficiario,
    CoberturaPoliza,
    EstadoPoliza,
    Poliza,
    RamoPoliza,
)

VERSION_TARIFAS_OPCIONALES = "2026.11.1"
PRECISION_MONEDA = Decimal("0.01")
DIAS_POR_MES = Decimal("30")
CIEN = Decimal("100")
MAX_BENEFICIARIOS = 10


@dataclass(frozen=True)
class DefinicionCoberturaOpcional:
    codigo: str
    nombre: str
    descripcion: str
    tasa_mensual: Decimal
    suma_minima: Decimal
    suma_maxima: Decimal
    # La suma no puede superar la de la cobertura principal (amparos accesorios de vida).
    hasta_suma_principal: bool = False


COBERTURAS_OPCIONALES: dict[RamoPoliza, tuple[DefinicionCoberturaOpcional, ...]] = {
    RamoPoliza.VIDA: (
        DefinicionCoberturaOpcional(
            codigo="INCAPACIDAD_TOTAL_PERMANENTE",
            nombre="Incapacidad total y permanente",
            descripcion="Anticipa la suma asegurada si el asegurado pierde de forma total y "
            "permanente su capacidad laboral.",
            tasa_mensual=Decimal("0.00012"),
            suma_minima=Decimal("1000000.00"),
            suma_maxima=Decimal("500000000.00"),
            hasta_suma_principal=True,
        ),
        DefinicionCoberturaOpcional(
            codigo="ENFERMEDADES_GRAVES",
            nombre="Enfermedades graves",
            descripcion="Pago único ante el primer diagnóstico de una enfermedad grave cubierta.",
            tasa_mensual=Decimal("0.00020"),
            suma_minima=Decimal("1000000.00"),
            suma_maxima=Decimal("200000000.00"),
            hasta_suma_principal=True,
        ),
        DefinicionCoberturaOpcional(
            codigo="AUXILIO_FUNERARIO",
            nombre="Auxilio funerario",
            descripcion="Reembolso de los gastos funerarios hasta el límite contratado.",
            tasa_mensual=Decimal("0.00030"),
            suma_minima=Decimal("1000000.00"),
            suma_maxima=Decimal("10000000.00"),
        ),
    ),
    RamoPoliza.VIAJE: (
        DefinicionCoberturaOpcional(
            codigo="CANCELACION_VIAJE",
            nombre="Cancelación del viaje",
            descripcion="Reembolso de los gastos no recuperables si el viaje se cancela por "
            "una causa cubierta.",
            tasa_mensual=Decimal("0.00400"),
            suma_minima=Decimal("500000.00"),
            suma_maxima=Decimal("20000000.00"),
        ),
        DefinicionCoberturaOpcional(
            codigo="EQUIPAJE",
            nombre="Pérdida de equipaje",
            descripcion="Indemnización por pérdida o daño del equipaje registrado.",
            tasa_mensual=Decimal("0.00300"),
            suma_minima=Decimal("500000.00"),
            suma_maxima=Decimal("10000000.00"),
        ),
    ),
    RamoPoliza.PROTECCION_DISPOSITIVOS: (
        DefinicionCoberturaOpcional(
            codigo="ACCESORIOS",
            nombre="Accesorios del dispositivo",
            descripcion="Cargador, audífonos y estuche originales contra daño y hurto.",
            tasa_mensual=Decimal("0.00600"),
            suma_minima=Decimal("100000.00"),
            suma_maxima=Decimal("3000000.00"),
        ),
        DefinicionCoberturaOpcional(
            codigo="GARANTIA_EXTENDIDA",
            nombre="Garantía extendida",
            descripcion="Reparación de fallas de fábrica después de la garantía del fabricante.",
            tasa_mensual=Decimal("0.00400"),
            suma_minima=Decimal("100000.00"),
            suma_maxima=Decimal("20000000.00"),
            hasta_suma_principal=True,
        ),
    ),
    # El paramétrico paga un monto fijo al cumplirse el índice: no tiene amparos opcionales.
    RamoPoliza.PARAMETRICO: (),
}

RAMOS_CON_BENEFICIARIOS = frozenset({RamoPoliza.VIDA})


def coberturas_disponibles(ramo: RamoPoliza) -> tuple[DefinicionCoberturaOpcional, ...]:
    return COBERTURAS_OPCIONALES.get(ramo, ())


def admite_beneficiarios(ramo: RamoPoliza) -> bool:
    return ramo in RAMOS_CON_BENEFICIARIOS


# --- Errores ----------------------------------------------------------------------------


class CodigoModificacion(str, Enum):
    SIN_CAMBIOS = "SIN_CAMBIOS"
    BENEFICIARIOS_NO_APLICAN = "BENEFICIARIOS_NO_APLICAN"
    DEMASIADOS_BENEFICIARIOS = "DEMASIADOS_BENEFICIARIOS"
    BENEFICIARIO_DUPLICADO = "BENEFICIARIO_DUPLICADO"
    BENEFICIARIO_ES_TITULAR = "BENEFICIARIO_ES_TITULAR"
    PORCENTAJES_NO_SUMAN_100 = "PORCENTAJES_NO_SUMAN_100"
    COBERTURA_NO_DISPONIBLE = "COBERTURA_NO_DISPONIBLE"
    COBERTURA_DUPLICADA = "COBERTURA_DUPLICADA"
    SUMA_FUERA_DE_RANGO = "SUMA_FUERA_DE_RANGO"


class ModificacionInvalida(ValueError):
    """La solicitud no cumple una regla del endoso. Se responde con un código estable."""

    def __init__(self, codigo: CodigoModificacion, mensaje: str, campo: str | None = None):
        self.codigo = codigo
        self.mensaje = mensaje
        self.campo = campo
        super().__init__(mensaje)


class PolizaNoModificable(Exception):
    """La póliza está vencida o cancelada: ya no admite endosos."""

    def __init__(self, estado: EstadoPoliza):
        self.estado = estado
        super().__init__(estado.value)


# --- Solicitud y propuesta --------------------------------------------------------------


class CoberturaSolicitada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    codigo: str = Field(min_length=1, max_length=50)
    suma_asegurada: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class SolicitudModificacion(BaseModel):
    """Estado deseado. `None` significa "no cambiar"; una lista vacía, "quitar todos"."""

    model_config = ConfigDict(extra="forbid")

    beneficiarios: list[Beneficiario] | None = Field(default=None, max_length=50)
    coberturas_opcionales: list[CoberturaSolicitada] | None = Field(default=None, max_length=20)


class TipoEndoso(str, Enum):
    BENEFICIARIOS = "BENEFICIARIOS"
    COBERTURAS = "COBERTURAS"
    BENEFICIARIOS_Y_COBERTURAS = "BENEFICIARIOS_Y_COBERTURAS"


class TipoCambio(str, Enum):
    BENEFICIARIO_AGREGADO = "BENEFICIARIO_AGREGADO"
    BENEFICIARIO_MODIFICADO = "BENEFICIARIO_MODIFICADO"
    BENEFICIARIO_RETIRADO = "BENEFICIARIO_RETIRADO"
    COBERTURA_INCLUIDA = "COBERTURA_INCLUIDA"
    COBERTURA_MODIFICADA = "COBERTURA_MODIFICADA"
    COBERTURA_EXCLUIDA = "COBERTURA_EXCLUIDA"


class CambioEndoso(BaseModel):
    """Linaje de un cambio: qué había antes y qué queda después (EC10, HU25)."""

    model_config = ConfigDict(extra="forbid")

    tipo: TipoCambio
    descripcion: str
    antes: dict[str, str] | None = None
    despues: dict[str, str] | None = None


class PropuestaEndoso(BaseModel):
    model_config = ConfigDict(extra="forbid")

    poliza_id: str
    tipo: TipoEndoso
    cambios: list[CambioEndoso]
    beneficiarios: list[Beneficiario]
    coberturas_opcionales: list[CoberturaPoliza]
    fecha_efecto: date
    dias_vigencia: int
    dias_restantes: int
    prima_opcionales_anterior: Decimal
    prima_opcionales_nueva: Decimal
    prima_anterior: Decimal
    ajuste_prima: Decimal
    prima_nueva: Decimal
    moneda: str
    version_tarifas: str = VERSION_TARIFAS_OPCIONALES


# --- Cálculo -----------------------------------------------------------------------------


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(PRECISION_MONEDA, rounding=ROUND_HALF_UP)


def dias_de_vigencia(poliza: Poliza) -> int:
    return (poliza.fecha_fin - poliza.fecha_inicio).days + 1


def fecha_de_efecto(poliza: Poliza, hoy: date) -> date:
    """El endoso rige desde hoy; si la póliza aún no empieza, desde su inicio."""
    return max(hoy, poliza.fecha_inicio)


def tarifa_cobertura(
    definicion: DefinicionCoberturaOpcional, suma: Decimal, dias_vigencia: int
) -> Decimal:
    """Prima de la cobertura opcional por toda la vigencia de la póliza."""
    meses = Decimal(dias_vigencia) / DIAS_POR_MES
    return _redondear(suma * definicion.tasa_mensual * meses)


def _definiciones(ramo: RamoPoliza) -> dict[str, DefinicionCoberturaOpcional]:
    return {d.codigo: d for d in coberturas_disponibles(ramo)}


def prima_de_opcionales(
    ramo: RamoPoliza, coberturas: list[CoberturaPoliza], dias_vigencia: int
) -> Decimal:
    definiciones = _definiciones(ramo)
    total = Decimal("0.00")
    for cobertura in coberturas:
        definicion = definiciones.get(cobertura.codigo)
        if definicion is not None:
            total += tarifa_cobertura(definicion, cobertura.suma_asegurada, dias_vigencia)
    return total


def validar_beneficiarios(poliza: Poliza, beneficiarios: list[Beneficiario]) -> list[Beneficiario]:
    if not admite_beneficiarios(poliza.ramo):
        raise ModificacionInvalida(
            CodigoModificacion.BENEFICIARIOS_NO_APLICAN,
            "Esta póliza no admite beneficiarios designados.",
            "beneficiarios",
        )
    if len(beneficiarios) > MAX_BENEFICIARIOS:
        raise ModificacionInvalida(
            CodigoModificacion.DEMASIADOS_BENEFICIARIOS,
            f"Puedes designar hasta {MAX_BENEFICIARIOS} beneficiarios.",
            "beneficiarios",
        )

    titular = (poliza.titular_tipo_documento, poliza.titular_numero_documento.upper())
    vistos: set[tuple[str, str]] = set()
    for indice, beneficiario in enumerate(beneficiarios):
        campo = f"beneficiarios[{indice}].numero_documento"
        if beneficiario.clave == titular:
            raise ModificacionInvalida(
                CodigoModificacion.BENEFICIARIO_ES_TITULAR,
                "El asegurado no puede ser beneficiario de su propia póliza de vida.",
                campo,
            )
        if beneficiario.clave in vistos:
            raise ModificacionInvalida(
                CodigoModificacion.BENEFICIARIO_DUPLICADO,
                "Hay dos beneficiarios con el mismo documento.",
                campo,
            )
        vistos.add(beneficiario.clave)

    # Sin beneficiarios designados, la indemnización va a los herederos legales.
    total = sum((b.porcentaje for b in beneficiarios), Decimal("0"))
    if beneficiarios and total != CIEN:
        raise ModificacionInvalida(
            CodigoModificacion.PORCENTAJES_NO_SUMAN_100,
            f"Los porcentajes de los beneficiarios deben sumar exactamente 100%; suman {total}%.",
            "beneficiarios",
        )
    return [b.model_copy() for b in beneficiarios]


def construir_coberturas(
    poliza: Poliza, solicitadas: list[CoberturaSolicitada]
) -> list[CoberturaPoliza]:
    definiciones = _definiciones(poliza.ramo)
    vistas: set[str] = set()
    resultado: dict[str, CoberturaPoliza] = {}
    for indice, solicitada in enumerate(solicitadas):
        campo = f"coberturas_opcionales[{indice}]"
        definicion = definiciones.get(solicitada.codigo)
        if definicion is None:
            raise ModificacionInvalida(
                CodigoModificacion.COBERTURA_NO_DISPONIBLE,
                "La cobertura no está disponible para este seguro.",
                f"{campo}.codigo",
            )
        if solicitada.codigo in vistas:
            raise ModificacionInvalida(
                CodigoModificacion.COBERTURA_DUPLICADA,
                "La cobertura está repetida en la solicitud.",
                f"{campo}.codigo",
            )
        vistas.add(solicitada.codigo)

        maxima = definicion.suma_maxima
        if definicion.hasta_suma_principal:
            maxima = min(maxima, poliza.cobertura_principal.suma_asegurada)
        if not definicion.suma_minima <= solicitada.suma_asegurada <= maxima:
            raise ModificacionInvalida(
                CodigoModificacion.SUMA_FUERA_DE_RANGO,
                f"La suma asegurada de {definicion.nombre} debe estar entre "
                f"{definicion.suma_minima} y {maxima} {poliza.moneda}.",
                f"{campo}.suma_asegurada",
            )
        resultado[definicion.codigo] = CoberturaPoliza(
            codigo=definicion.codigo,
            nombre=definicion.nombre,
            suma_asegurada=solicitada.suma_asegurada,
            descripcion=definicion.descripcion,
        )
    # Mismo orden que el catálogo: la propuesta y el documento salen siempre iguales.
    return [resultado[c] for c in definiciones if c in resultado]


def _ficha_beneficiario(b: Beneficiario) -> dict[str, str]:
    return {
        "nombre_completo": b.nombre_completo,
        "documento": f"{b.tipo_documento} {b.numero_documento}",
        "parentesco": b.parentesco,
        "porcentaje": f"{b.porcentaje:.2f}",
    }


def _ficha_cobertura(c: CoberturaPoliza) -> dict[str, str]:
    return {"codigo": c.codigo, "nombre": c.nombre, "suma_asegurada": f"{c.suma_asegurada:.2f}"}


def _cambios_beneficiarios(
    antes: list[Beneficiario], despues: list[Beneficiario]
) -> list[CambioEndoso]:
    previos = {b.clave: b for b in antes}
    nuevos = {b.clave: b for b in despues}
    cambios: list[CambioEndoso] = []
    for clave, nuevo in nuevos.items():
        previo = previos.get(clave)
        if previo is None:
            cambios.append(
                CambioEndoso(
                    tipo=TipoCambio.BENEFICIARIO_AGREGADO,
                    descripcion=f"Se designa a {nuevo.nombre_completo} con {nuevo.porcentaje}%.",
                    despues=_ficha_beneficiario(nuevo),
                )
            )
        elif _ficha_beneficiario(previo) != _ficha_beneficiario(nuevo):
            cambios.append(
                CambioEndoso(
                    tipo=TipoCambio.BENEFICIARIO_MODIFICADO,
                    descripcion=f"Se actualizan los datos de {nuevo.nombre_completo}.",
                    antes=_ficha_beneficiario(previo),
                    despues=_ficha_beneficiario(nuevo),
                )
            )
    for clave, previo in previos.items():
        if clave not in nuevos:
            cambios.append(
                CambioEndoso(
                    tipo=TipoCambio.BENEFICIARIO_RETIRADO,
                    descripcion=f"Se retira a {previo.nombre_completo} como beneficiario.",
                    antes=_ficha_beneficiario(previo),
                )
            )
    return cambios


def _cambios_coberturas(
    antes: list[CoberturaPoliza], despues: list[CoberturaPoliza]
) -> list[CambioEndoso]:
    previas = {c.codigo: c for c in antes}
    nuevas = {c.codigo: c for c in despues}
    cambios: list[CambioEndoso] = []
    for codigo, nueva in nuevas.items():
        previa = previas.get(codigo)
        if previa is None:
            cambios.append(
                CambioEndoso(
                    tipo=TipoCambio.COBERTURA_INCLUIDA,
                    descripcion=f"Se incluye {nueva.nombre}.",
                    despues=_ficha_cobertura(nueva),
                )
            )
        elif previa.suma_asegurada != nueva.suma_asegurada:
            cambios.append(
                CambioEndoso(
                    tipo=TipoCambio.COBERTURA_MODIFICADA,
                    descripcion=f"Se ajusta la suma asegurada de {nueva.nombre}.",
                    antes=_ficha_cobertura(previa),
                    despues=_ficha_cobertura(nueva),
                )
            )
    for codigo, previa in previas.items():
        if codigo not in nuevas:
            cambios.append(
                CambioEndoso(
                    tipo=TipoCambio.COBERTURA_EXCLUIDA,
                    descripcion=f"Se excluye {previa.nombre}.",
                    antes=_ficha_cobertura(previa),
                )
            )
    return cambios


def proponer_endoso(poliza: Poliza, solicitud: SolicitudModificacion, hoy: date) -> PropuestaEndoso:
    """Valida la solicitud contra la póliza y calcula el endoso, sin guardar nada."""

    estado = poliza.estado_en(hoy)
    if estado is not EstadoPoliza.VIGENTE:
        raise PolizaNoModificable(estado)

    beneficiarios = poliza.beneficiarios
    cambios_beneficiarios: list[CambioEndoso] = []
    if solicitud.beneficiarios is not None:
        beneficiarios = validar_beneficiarios(poliza, solicitud.beneficiarios)
        cambios_beneficiarios = _cambios_beneficiarios(poliza.beneficiarios, beneficiarios)

    coberturas = poliza.coberturas_opcionales
    cambios_coberturas: list[CambioEndoso] = []
    if solicitud.coberturas_opcionales is not None:
        coberturas = construir_coberturas(poliza, solicitud.coberturas_opcionales)
        cambios_coberturas = _cambios_coberturas(poliza.coberturas_opcionales, coberturas)

    if not cambios_beneficiarios and not cambios_coberturas:
        raise ModificacionInvalida(
            CodigoModificacion.SIN_CAMBIOS, "La solicitud no cambia nada de la póliza."
        )

    if cambios_beneficiarios and cambios_coberturas:
        tipo = TipoEndoso.BENEFICIARIOS_Y_COBERTURAS
    elif cambios_beneficiarios:
        tipo = TipoEndoso.BENEFICIARIOS
    else:
        tipo = TipoEndoso.COBERTURAS

    dias_vigencia = dias_de_vigencia(poliza)
    efecto = fecha_de_efecto(poliza, hoy)
    dias_restantes = (poliza.fecha_fin - efecto).days + 1
    anterior = prima_de_opcionales(poliza.ramo, poliza.coberturas_opcionales, dias_vigencia)
    nueva = prima_de_opcionales(poliza.ramo, coberturas, dias_vigencia)
    ajuste = _redondear((nueva - anterior) * Decimal(dias_restantes) / Decimal(dias_vigencia))

    return PropuestaEndoso(
        poliza_id=poliza.poliza_id,
        tipo=tipo,
        cambios=cambios_beneficiarios + cambios_coberturas,
        beneficiarios=beneficiarios,
        coberturas_opcionales=coberturas,
        fecha_efecto=efecto,
        dias_vigencia=dias_vigencia,
        dias_restantes=dias_restantes,
        prima_opcionales_anterior=anterior,
        prima_opcionales_nueva=nueva,
        prima_anterior=poliza.prima_total,
        ajuste_prima=ajuste,
        prima_nueva=poliza.prima_total + ajuste,
        moneda=poliza.moneda,
    )


# --- Endoso registrado ------------------------------------------------------------------


class Endoso(BaseModel):
    """Endoso confirmado. Es inmutable: un cambio posterior genera un endoso nuevo."""

    model_config = ConfigDict(extra="forbid")

    endoso_id: str = Field(min_length=1, max_length=60)
    poliza_id: str = Field(min_length=1, max_length=50)
    numero_endoso: int = Field(ge=1)
    tipo: TipoEndoso
    solicitado_por: str = Field(min_length=1, max_length=50)
    rol_solicitante: str = Field(min_length=1, max_length=40)
    clave_idempotencia: str | None = Field(default=None, max_length=100)
    huella_solicitud: str = Field(min_length=64, max_length=64)
    ip_solicitante: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=300)
    fecha_efecto: date
    dias_vigencia: int = Field(ge=1)
    dias_restantes: int = Field(ge=1)
    prima_anterior: Decimal
    ajuste_prima: Decimal
    prima_nueva: Decimal = Field(gt=0)
    moneda: str = Field(pattern=r"^[A-Z]{3}$")
    cambios: list[CambioEndoso] = Field(min_length=1)
    coberturas_opcionales: list[CoberturaPoliza]
    beneficiarios: list[Beneficiario]
    clave_documento: str = Field(min_length=1, max_length=200)
    huella_documento: str = Field(min_length=64, max_length=64)
    tamano_documento: int = Field(gt=0)
    creado_en: AwareDatetime

    @property
    def es_cobro(self) -> bool:
        return self.ajuste_prima > 0

    @property
    def es_devolucion(self) -> bool:
        return self.ajuste_prima < 0


def endoso_id_de(poliza_id: str, numero: int) -> str:
    return f"END-{poliza_id.removeprefix('POL-')}-{numero:03d}"
