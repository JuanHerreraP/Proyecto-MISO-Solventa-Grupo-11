"""Validación de los datos de riesgo requeridos por cada ramo (HU03 / BPM-153)."""

from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.cotizaciones.dominio.catalogo import CampoRiesgo, TipoCampo, consultar_ramo
from app.cotizaciones.dominio.modelos import RamoSeguro


class CodigoErrorDato(str, Enum):
    """Códigos estables para que los clientes identifiquen el problema de cada campo."""

    REQUERIDO = "REQUERIDO"
    TIPO_INVALIDO = "TIPO_INVALIDO"
    VALOR_INVALIDO = "VALOR_INVALIDO"
    CAMPO_NO_PERMITIDO = "CAMPO_NO_PERMITIDO"


class ErrorDatoRiesgo(BaseModel):
    """Detalle estructurado de un campo que impide completar la cotización."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    campo: str = Field(min_length=1)
    codigo: CodigoErrorDato
    mensaje: str = Field(min_length=1)


class DatosRiesgoInvalidosError(ValueError):
    """Error de dominio que conserva todos los problemas encontrados en la solicitud."""

    def __init__(self, errores: list[ErrorDatoRiesgo]) -> None:
        self.errores = tuple(errores)
        super().__init__("Los datos del riesgo no son válidos.")


def validar_datos_riesgo(
    ramo: RamoSeguro,
    datos: dict[str, object],
) -> dict[str, object]:
    """Valida y normaliza los datos sin depender de FastAPI ni de un canal específico."""

    definicion = consultar_ramo(ramo)
    campos_por_codigo = {campo.codigo: campo for campo in definicion.campos}
    errores: list[ErrorDatoRiesgo] = []
    normalizados: dict[str, object] = {}

    for codigo in sorted(set(datos) - set(campos_por_codigo)):
        errores.append(
            ErrorDatoRiesgo(
                campo=codigo,
                codigo=CodigoErrorDato.CAMPO_NO_PERMITIDO,
                mensaje="El campo no pertenece al ramo seleccionado.",
            )
        )

    for campo in definicion.campos:
        valor = datos.get(campo.codigo)
        if valor is None:
            if campo.requerido:
                errores.append(
                    ErrorDatoRiesgo(
                        campo=campo.codigo,
                        codigo=CodigoErrorDato.REQUERIDO,
                        mensaje="El campo es obligatorio.",
                    )
                )
            continue

        try:
            normalizados[campo.codigo] = _normalizar_valor(campo, valor)
        except TypeError as error:
            errores.append(
                ErrorDatoRiesgo(
                    campo=campo.codigo,
                    codigo=CodigoErrorDato.TIPO_INVALIDO,
                    mensaje=str(error),
                )
            )
        except ValueError as error:
            errores.append(
                ErrorDatoRiesgo(
                    campo=campo.codigo,
                    codigo=CodigoErrorDato.VALOR_INVALIDO,
                    mensaje=str(error),
                )
            )

    _validar_reglas_del_ramo(ramo, normalizados, errores)

    if errores:
        raise DatosRiesgoInvalidosError(errores)
    return normalizados


def _normalizar_valor(campo: CampoRiesgo, valor: object) -> object:
    if campo.tipo is TipoCampo.TEXTO:
        return _normalizar_texto(valor)

    if campo.tipo is TipoCampo.OPCION:
        opcion = _normalizar_texto(valor)
        if opcion not in campo.opciones:
            permitidas = ", ".join(campo.opciones)
            raise ValueError(f"Debe ser una de estas opciones: {permitidas}.")
        return opcion

    if campo.tipo is TipoCampo.ENTERO:
        if type(valor) is not int:
            raise TypeError("Debe ser un número entero.")
        return valor

    if campo.tipo is TipoCampo.DECIMAL:
        if isinstance(valor, bool) or not isinstance(valor, (Decimal, int, float, str)):
            raise TypeError("Debe ser un número decimal.")
        try:
            decimal = Decimal(str(valor))
        except InvalidOperation as error:
            raise ValueError("Debe contener un número decimal válido.") from error
        if not decimal.is_finite():
            raise ValueError("Debe contener un número decimal finito.")
        return decimal

    if campo.tipo is TipoCampo.FECHA:
        if type(valor) is date:
            return valor
        if not isinstance(valor, str):
            raise TypeError("Debe ser una fecha en formato AAAA-MM-DD.")
        try:
            return date.fromisoformat(valor)
        except ValueError as error:
            raise ValueError("Debe ser una fecha válida en formato AAAA-MM-DD.") from error

    if campo.tipo is TipoCampo.BOOLEANO:
        if type(valor) is not bool:
            raise TypeError("Debe ser un valor booleano.")
        return valor

    raise ValueError("El tipo de campo no está soportado.")


def _normalizar_texto(valor: object) -> str:
    if not isinstance(valor, str):
        raise TypeError("Debe ser un texto.")
    texto = valor.strip()
    if not texto:
        raise ValueError("No puede estar vacío.")
    return texto


def _validar_reglas_del_ramo(
    ramo: RamoSeguro,
    datos: dict[str, object],
    errores: list[ErrorDatoRiesgo],
) -> None:
    if ramo is RamoSeguro.VIAJE:
        _validar_periodo(datos, errores)
        _validar_positivos(datos, ("numero_viajeros", "valor_asegurado"), errores)
        return

    if ramo is RamoSeguro.PROTECCION_DISPOSITIVOS:
        _validar_positivos(datos, ("valor_dispositivo", "meses_cobertura"), errores)
        _validar_fecha_no_futura(datos, "fecha_compra", errores)
        return

    if ramo is RamoSeguro.VIDA:
        _validar_positivos(datos, ("valor_asegurado", "meses_cobertura"), errores)
        _validar_fecha_pasada(datos, "fecha_nacimiento", errores)
        return

    if ramo is RamoSeguro.PARAMETRICO:
        _validar_periodo(datos, errores)
        _validar_positivos(datos, ("umbral_disparo", "valor_asegurado"), errores)
        _validar_datos_del_evento_parametrico(datos, errores)


def _validar_periodo(
    datos: dict[str, object],
    errores: list[ErrorDatoRiesgo],
) -> None:
    inicio = datos.get("fecha_inicio")
    fin = datos.get("fecha_fin")
    if type(inicio) is date and type(fin) is date and fin <= inicio:
        errores.append(
            ErrorDatoRiesgo(
                campo="fecha_fin",
                codigo=CodigoErrorDato.VALOR_INVALIDO,
                mensaje="Debe ser posterior a la fecha de inicio.",
            )
        )


def _validar_positivos(
    datos: dict[str, object],
    campos: tuple[str, ...],
    errores: list[ErrorDatoRiesgo],
) -> None:
    for campo in campos:
        valor = datos.get(campo)
        if isinstance(valor, (Decimal, int)) and not isinstance(valor, bool) and valor <= 0:
            errores.append(
                ErrorDatoRiesgo(
                    campo=campo,
                    codigo=CodigoErrorDato.VALOR_INVALIDO,
                    mensaje="Debe ser mayor que cero.",
                )
            )


def _validar_fecha_no_futura(
    datos: dict[str, object],
    campo: str,
    errores: list[ErrorDatoRiesgo],
) -> None:
    valor = datos.get(campo)
    if type(valor) is date and valor > date.today():
        errores.append(
            ErrorDatoRiesgo(
                campo=campo,
                codigo=CodigoErrorDato.VALOR_INVALIDO,
                mensaje="No puede ser una fecha futura.",
            )
        )


def _validar_fecha_pasada(
    datos: dict[str, object],
    campo: str,
    errores: list[ErrorDatoRiesgo],
) -> None:
    valor = datos.get(campo)
    if type(valor) is date and valor >= date.today():
        errores.append(
            ErrorDatoRiesgo(
                campo=campo,
                codigo=CodigoErrorDato.VALOR_INVALIDO,
                mensaje="Debe ser una fecha anterior a hoy.",
            )
        )


def _validar_datos_del_evento_parametrico(
    datos: dict[str, object],
    errores: list[ErrorDatoRiesgo],
) -> None:
    tipo_evento = datos.get("tipo_evento")
    campo_condicional = {
        "RETRASO_VUELO": "numero_vuelo",
        "EVENTO_CLIMATICO": "ubicacion",
    }.get(tipo_evento)

    if campo_condicional is not None and campo_condicional not in datos:
        errores.append(
            ErrorDatoRiesgo(
                campo=campo_condicional,
                codigo=CodigoErrorDato.REQUERIDO,
                mensaje="El campo es obligatorio para el tipo de evento seleccionado.",
            )
        )
