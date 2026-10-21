"""Catálogo de ramos y datos de riesgo requeridos para cotizar (HU03 / BPM-152)."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.cotizaciones.dominio.modelos import RamoSeguro


class TipoCampo(str, Enum):
    """Tipos neutrales que pueden representar los distintos clientes de Solventa."""

    TEXTO = "TEXTO"
    ENTERO = "ENTERO"
    DECIMAL = "DECIMAL"
    FECHA = "FECHA"
    BOOLEANO = "BOOLEANO"
    OPCION = "OPCION"


class CampoRiesgo(BaseModel):
    """Definición de un dato que debe solicitarse para evaluar un riesgo."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    codigo: str = Field(min_length=1, max_length=60, pattern=r"^[a-z][a-z0-9_]*$")
    etiqueta: str = Field(min_length=2, max_length=100)
    tipo: TipoCampo
    requerido: bool = True
    descripcion: str = Field(min_length=2, max_length=300)
    unidad: str | None = Field(default=None, min_length=1, max_length=20)
    opciones: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validar_opciones(self) -> "CampoRiesgo":
        if self.tipo is TipoCampo.OPCION and not self.opciones:
            raise ValueError("Un campo de opción debe declarar sus valores permitidos.")
        if self.tipo is not TipoCampo.OPCION and self.opciones:
            raise ValueError("Solo los campos de opción pueden declarar valores permitidos.")
        if len(self.opciones) != len(set(self.opciones)):
            raise ValueError("Las opciones de un campo no pueden repetirse.")
        return self


class DefinicionRamo(BaseModel):
    """Contrato de entrada requerido para cotizar un ramo."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    ramo: RamoSeguro
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: str = Field(min_length=2, max_length=300)
    campos: tuple[CampoRiesgo, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validar_codigos_unicos(self) -> "DefinicionRamo":
        codigos = [campo.codigo for campo in self.campos]
        if len(codigos) != len(set(codigos)):
            raise ValueError("Los campos de un ramo no pueden repetir el código.")
        return self


CATALOGO_RAMOS: tuple[DefinicionRamo, ...] = (
    DefinicionRamo(
        ramo=RamoSeguro.VIAJE,
        nombre="Seguro de viaje",
        descripcion="Protección durante un viaje dentro del periodo contratado.",
        campos=(
            CampoRiesgo(
                codigo="destino",
                etiqueta="Destino",
                tipo=TipoCampo.TEXTO,
                descripcion="País o ciudad principal del viaje.",
            ),
            CampoRiesgo(
                codigo="fecha_inicio",
                etiqueta="Fecha de inicio",
                tipo=TipoCampo.FECHA,
                descripcion="Primer día de cobertura del viaje.",
            ),
            CampoRiesgo(
                codigo="fecha_fin",
                etiqueta="Fecha de finalización",
                tipo=TipoCampo.FECHA,
                descripcion="Último día de cobertura del viaje.",
            ),
            CampoRiesgo(
                codigo="numero_viajeros",
                etiqueta="Número de viajeros",
                tipo=TipoCampo.ENTERO,
                descripcion="Cantidad de personas que estarán cubiertas.",
            ),
            CampoRiesgo(
                codigo="valor_asegurado",
                etiqueta="Valor asegurado",
                tipo=TipoCampo.DECIMAL,
                descripcion="Monto máximo de protección solicitado.",
                unidad="COP",
            ),
        ),
    ),
    DefinicionRamo(
        ramo=RamoSeguro.PROTECCION_DISPOSITIVOS,
        nombre="Protección de dispositivos",
        descripcion="Protección de un dispositivo personal contra los riesgos contratados.",
        campos=(
            CampoRiesgo(
                codigo="tipo_dispositivo",
                etiqueta="Tipo de dispositivo",
                tipo=TipoCampo.OPCION,
                descripcion="Clase de dispositivo que se desea proteger.",
                opciones=("CELULAR", "TABLETA", "PORTATIL"),
            ),
            CampoRiesgo(
                codigo="marca",
                etiqueta="Marca",
                tipo=TipoCampo.TEXTO,
                descripcion="Fabricante del dispositivo.",
            ),
            CampoRiesgo(
                codigo="modelo",
                etiqueta="Modelo",
                tipo=TipoCampo.TEXTO,
                descripcion="Referencia comercial del dispositivo.",
            ),
            CampoRiesgo(
                codigo="valor_dispositivo",
                etiqueta="Valor del dispositivo",
                tipo=TipoCampo.DECIMAL,
                descripcion="Valor comercial declarado del dispositivo.",
                unidad="COP",
            ),
            CampoRiesgo(
                codigo="fecha_compra",
                etiqueta="Fecha de compra",
                tipo=TipoCampo.FECHA,
                descripcion="Fecha en que fue adquirido el dispositivo.",
            ),
            CampoRiesgo(
                codigo="meses_cobertura",
                etiqueta="Meses de cobertura",
                tipo=TipoCampo.ENTERO,
                descripcion="Duración solicitada para la protección.",
                unidad="meses",
            ),
        ),
    ),
    DefinicionRamo(
        ramo=RamoSeguro.VIDA,
        nombre="Microseguro de vida",
        descripcion="Protección económica de vida por el periodo contratado.",
        campos=(
            CampoRiesgo(
                codigo="fecha_nacimiento",
                etiqueta="Fecha de nacimiento",
                tipo=TipoCampo.FECHA,
                descripcion="Fecha de nacimiento de la persona asegurada.",
            ),
            CampoRiesgo(
                codigo="valor_asegurado",
                etiqueta="Valor asegurado",
                tipo=TipoCampo.DECIMAL,
                descripcion="Monto de protección solicitado.",
                unidad="COP",
            ),
            CampoRiesgo(
                codigo="meses_cobertura",
                etiqueta="Meses de cobertura",
                tipo=TipoCampo.ENTERO,
                descripcion="Duración solicitada para la protección.",
                unidad="meses",
            ),
            CampoRiesgo(
                codigo="fumador",
                etiqueta="¿Es fumador?",
                tipo=TipoCampo.BOOLEANO,
                descripcion="Indica si la persona asegurada consume tabaco.",
            ),
        ),
    ),
    DefinicionRamo(
        ramo=RamoSeguro.PARAMETRICO,
        nombre="Seguro paramétrico",
        descripcion="Protección activada al cumplirse una condición objetiva de clima o vuelo.",
        campos=(
            CampoRiesgo(
                codigo="tipo_evento",
                etiqueta="Tipo de evento",
                tipo=TipoCampo.OPCION,
                descripcion="Evento objetivo que activaría la cobertura.",
                opciones=("RETRASO_VUELO", "EVENTO_CLIMATICO"),
            ),
            CampoRiesgo(
                codigo="fecha_inicio",
                etiqueta="Fecha de inicio",
                tipo=TipoCampo.FECHA,
                descripcion="Primer día del periodo de observación.",
            ),
            CampoRiesgo(
                codigo="fecha_fin",
                etiqueta="Fecha de finalización",
                tipo=TipoCampo.FECHA,
                descripcion="Último día del periodo de observación.",
            ),
            CampoRiesgo(
                codigo="umbral_disparo",
                etiqueta="Umbral de activación",
                tipo=TipoCampo.DECIMAL,
                descripcion="Valor objetivo que activa automáticamente la cobertura.",
            ),
            CampoRiesgo(
                codigo="valor_asegurado",
                etiqueta="Valor asegurado",
                tipo=TipoCampo.DECIMAL,
                descripcion="Monto pagadero cuando se cumple la condición contratada.",
                unidad="COP",
            ),
            CampoRiesgo(
                codigo="numero_vuelo",
                etiqueta="Número de vuelo",
                tipo=TipoCampo.TEXTO,
                requerido=False,
                descripcion="Identificador requerido cuando el evento corresponde a un vuelo.",
            ),
            CampoRiesgo(
                codigo="ubicacion",
                etiqueta="Ubicación",
                tipo=TipoCampo.TEXTO,
                requerido=False,
                descripcion="Lugar requerido cuando el evento corresponde al clima.",
            ),
        ),
    ),
)


def consultar_catalogo_ramos() -> tuple[DefinicionRamo, ...]:
    """Retorna todos los ramos disponibles para cotización."""

    return CATALOGO_RAMOS


def consultar_ramo(ramo: RamoSeguro) -> DefinicionRamo:
    """Retorna la definición de datos de riesgo correspondiente a un ramo."""

    return next(definicion for definicion in CATALOGO_RAMOS if definicion.ramo is ramo)
