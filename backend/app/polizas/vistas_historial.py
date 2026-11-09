"""Vista consolidada del historial de movimientos de una póliza (HU25 / CPM-72).

HU25 es estrictamente de **lectura**: no crea movimientos ni tablas nuevas. Normaliza lo que
ya registran otros módulos (emisión HU12, pago inicial HU13, endosos HU16, desembolsos HU15)
en un modelo neutral `MovimientoPoliza` y lo ordena del más reciente al más antiguo.

El diseño deja preparado agregar fuentes futuras (renovaciones, cancelaciones con entidad
propia, pagos periódicos) sin cambiar el contrato público: basta mapear la nueva fuente a
`MovimientoPoliza` y sumarla a la lista antes de ordenar.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.desembolsos.modelos import Desembolso, EstadoDesembolso
from app.pagos.modelos import Pago
from app.polizas.dominio.endosos import CambioEndoso, Endoso
from app.polizas.dominio.modelos import Poliza


class CategoriaMovimiento(str, Enum):
    """Agrupa el movimiento para que la UI lo pinte distinto."""

    FINANCIERO = "FINANCIERO"
    CONTRACTUAL = "CONTRACTUAL"
    POLIZA = "POLIZA"


class TipoMovimiento(str, Enum):
    """Tipos soportados hoy. Se amplía cuando aparezcan las HU correspondientes."""

    EMISION = "EMISION"
    PAGO_PRIMA_INICIAL = "PAGO_PRIMA_INICIAL"
    ENDOSO = "ENDOSO"
    RENOVACION = "RENOVACION"
    CANCELACION = "CANCELACION"
    DESEMBOLSO_INDEMNIZACION = "DESEMBOLSO_INDEMNIZACION"
    REEMBOLSO = "REEMBOLSO"


class NaturalezaMonto(str, Enum):
    """Sentido del dinero desde la perspectiva del cliente. El monto siempre es positivo."""

    COBRO = "COBRO"
    REEMBOLSO = "REEMBOLSO"
    INDEMNIZACION = "INDEMNIZACION"
    AJUSTE = "AJUSTE"


class CambioHistorial(BaseModel):
    """Linaje de un cambio contractual: qué cambió, valor anterior y valor nuevo (HU25)."""

    model_config = ConfigDict(extra="forbid")

    tipo: str
    descripcion: str
    antes: dict[str, str] | None = None
    despues: dict[str, str] | None = None


class ConsentimientoHistorial(BaseModel):
    """Evidencia del consentimiento explícito del cliente para un movimiento contractual.

    Para endosos (HU16), el backend no permite confirmar sin `acepta_condiciones=true`, así que
    un endoso registrado implica aceptación explícita. No se exponen IP ni user-agent al cliente
    (principio de mínimo privilegio); quedan para una vista interna de auditoría futura.
    """

    model_config = ConfigDict(extra="forbid")

    explicito: bool
    tipo: str
    usuario_id: str | None = None
    rol: str | None = None
    fecha: datetime | None = None
    huella_solicitud: str | None = None


class MovimientoPoliza(BaseModel):
    """Movimiento neutral del historial. No sustituye a Pago/Endoso/Desembolso: los normaliza."""

    model_config = ConfigDict(extra="forbid")

    movimiento_id: str
    poliza_id: str
    categoria: CategoriaMovimiento
    tipo: TipoMovimiento
    fecha: datetime
    descripcion: str
    referencia: str | None = None
    referencia_externa: str | None = None
    estado: str | None = None
    monto: Decimal | None = None
    moneda: str | None = None
    naturaleza_monto: NaturalezaMonto | None = None
    cambios: list[CambioHistorial] = []
    consentimiento: ConsentimientoHistorial | None = None


class HistorialPoliza(BaseModel):
    """Respuesta del endpoint: la bitácora, siempre del más reciente al más antiguo."""

    model_config = ConfigDict(extra="forbid")

    poliza_id: str
    numero_poliza: str
    movimientos: list[MovimientoPoliza]


# --- Normalización desde las fuentes de verdad -----------------------------------------


def movimiento_emision(poliza: Poliza) -> MovimientoPoliza:
    """La emisión de la póliza es el primer movimiento histórico (HU12). No es financiero."""
    return MovimientoPoliza(
        movimiento_id=f"{poliza.poliza_id}-EMISION",
        poliza_id=poliza.poliza_id,
        categoria=CategoriaMovimiento.POLIZA,
        tipo=TipoMovimiento.EMISION,
        fecha=poliza.emitida_en,
        descripcion="Póliza emitida",
        referencia=poliza.numero_poliza,
        estado="COMPLETADO",
    )


def movimiento_cancelacion(poliza: Poliza) -> MovimientoPoliza | None:
    """Movimiento básico de cancelación si la póliza registra `cancelada_en`.

    No se inventan motivo, usuario ni reembolso: esos datos no están persistidos en la póliza.
    Si más adelante existe una entidad de cancelación más completa (HU18), debe preferirse.
    """
    if poliza.cancelada_en is None:
        return None
    return MovimientoPoliza(
        movimiento_id=f"{poliza.poliza_id}-CANCELACION",
        poliza_id=poliza.poliza_id,
        categoria=CategoriaMovimiento.CONTRACTUAL,
        tipo=TipoMovimiento.CANCELACION,
        fecha=poliza.cancelada_en,
        descripcion="Póliza cancelada",
        referencia=poliza.numero_poliza,
        estado="COMPLETADO",
    )


def movimiento_pago(pago: Pago, poliza_id: str) -> MovimientoPoliza:
    """Pago del recaudo inicial (HU13). La referencia externa es la de la pasarela, si existe."""
    return MovimientoPoliza(
        movimiento_id=pago.pago_id,
        poliza_id=poliza_id,
        categoria=CategoriaMovimiento.FINANCIERO,
        tipo=TipoMovimiento.PAGO_PRIMA_INICIAL,
        fecha=pago.creado_en,
        descripcion="Pago de prima inicial",
        referencia=pago.pago_id,
        referencia_externa=pago.referencia_pasarela,
        estado=pago.estado.value,
        monto=pago.monto,
        moneda=pago.moneda,
        naturaleza_monto=NaturalezaMonto.COBRO,
    )


def _a_cambio_historial(cambio: CambioEndoso) -> CambioHistorial:
    return CambioHistorial(
        tipo=cambio.tipo.value,
        descripcion=cambio.descripcion,
        antes=cambio.antes,
        despues=cambio.despues,
    )


def _naturaleza_ajuste_endoso(endoso: Endoso) -> NaturalezaMonto | None:
    """El ajuste del endoso es contractual, no una transacción financiera ejecutada.

    Un ajuste positivo es un cobro pendiente; uno negativo, una devolución pendiente. Se expone
    como AJUSTE para no confundirlo con un pago realizado.
    """
    if endoso.ajuste_prima == 0:
        return None
    return NaturalezaMonto.AJUSTE


def movimiento_endoso(endoso: Endoso) -> MovimientoPoliza:
    """Endoso confirmado (HU16). Conserva el linaje antes/después y el consentimiento.

    El monto es el ajuste de prima en valor absoluto; `naturaleza_monto=AJUSTE` deja claro que
    es un cambio contractual y no un cobro o devolución ya procesados.
    """
    ajuste = abs(endoso.ajuste_prima) if endoso.ajuste_prima != 0 else None
    return MovimientoPoliza(
        movimiento_id=endoso.endoso_id,
        poliza_id=endoso.poliza_id,
        categoria=CategoriaMovimiento.CONTRACTUAL,
        tipo=TipoMovimiento.ENDOSO,
        fecha=endoso.creado_en,
        descripcion=f"Endoso #{endoso.numero_endoso}",
        referencia=endoso.endoso_id,
        estado="COMPLETADO",
        monto=ajuste,
        moneda=endoso.moneda if ajuste is not None else None,
        naturaleza_monto=_naturaleza_ajuste_endoso(endoso),
        cambios=[_a_cambio_historial(c) for c in endoso.cambios],
        consentimiento=ConsentimientoHistorial(
            explicito=True,
            tipo="CONFIRMACION_ENDOSO",
            usuario_id=endoso.solicitado_por,
            rol=endoso.rol_solicitante,
            fecha=endoso.creado_en,
            huella_solicitud=endoso.huella_solicitud,
        ),
    )


def movimiento_desembolso(desembolso: Desembolso) -> MovimientoPoliza:
    """Desembolso de indemnización (HU15): salida de dinero hacia el cliente."""
    return MovimientoPoliza(
        movimiento_id=desembolso.desembolso_id,
        poliza_id=desembolso.poliza_id,
        categoria=CategoriaMovimiento.FINANCIERO,
        tipo=TipoMovimiento.DESEMBOLSO_INDEMNIZACION,
        fecha=desembolso.creado_en,
        descripcion="Pago de indemnización por siniestro",
        referencia=desembolso.desembolso_id,
        referencia_externa=desembolso.referencia_transaccion,
        estado=desembolso.estado.value,
        monto=desembolso.monto,
        moneda=desembolso.moneda,
        naturaleza_monto=NaturalezaMonto.INDEMNIZACION,
    )


# Estados de desembolso que representan dinero en movimiento hacia el cliente. Un desembolso
# fallido no debería figurar como indemnización entregada en la bitácora.
ESTADOS_DESEMBOLSO_VISIBLES = frozenset({EstadoDesembolso.PENDIENTE, EstadoDesembolso.COMPLETADA})
