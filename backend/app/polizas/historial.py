"""Caso de uso del historial consolidado de una póliza (HU25 / CPM-72).

El servicio reúne los movimientos que otros módulos ya generaron, los normaliza a
`MovimientoPoliza` y los ordena del más reciente al más antiguo. No crea ni modifica nada:
es estrictamente de lectura.

Fuentes integradas hoy:
- Emisión (HU12): `poliza.emitida_en`.
- Pago inicial (HU13): pagos ligados por `poliza.cotizacion_id == pago.cotizacion_id`.
- Endosos (HU16): `endosos` de la póliza, con su linaje y consentimiento.
- Desembolsos (HU15): indemnizaciones de la póliza.
- Cancelación: movimiento básico si `poliza.cancelada_en` está presente.

Para agregar renovaciones (HU17), cancelaciones con entidad propia (HU18) o pagos periódicos
(HU21) basta añadir un método privado `_movimientos_*` y sumarlo en `_reunir`, sin tocar el
contrato público.
"""

from datetime import UTC, datetime
from typing import Protocol

from app.desembolsos.modelos import Desembolso
from app.polizas.dominio.endosos import Endoso
from app.polizas.dominio.modelos import Poliza, hoy_en_colombia
from app.polizas.vistas_historial import (
    ESTADOS_DESEMBOLSO_VISIBLES,
    HistorialPoliza,
    MovimientoPoliza,
    movimiento_cancelacion,
    movimiento_desembolso,
    movimiento_emision,
    movimiento_endoso,
    movimiento_pago,
)


class PolizaNoEncontrada(Exception):
    """La póliza no existe."""


class AccesoDenegadoHistorial(Exception):
    """El usuario no puede ver el historial de esta póliza."""


class RepositorioPolizasHistorial(Protocol):
    def obtener(self, poliza_id: str) -> Poliza | None: ...


class RepositorioPagosHistorial(Protocol):
    def listar_por_cotizacion(self, cotizacion_id: str) -> list[object]: ...


class RepositorioEndososHistorial(Protocol):
    def listar_por_poliza(self, poliza_id: str) -> list[Endoso]: ...


class RepositorioDesembolsosHistorial(Protocol):
    def listar_por_poliza(self, poliza_id: str) -> list[Desembolso]: ...


class ServicioHistorialPoliza:
    def __init__(
        self,
        polizas: RepositorioPolizasHistorial,
        pagos: RepositorioPagosHistorial,
        endosos: RepositorioEndososHistorial,
        desembolsos: RepositorioDesembolsosHistorial,
    ):
        self._polizas = polizas
        self._pagos = pagos
        self._endosos = endosos
        self._desembolsos = desembolsos

    def consultar(
        self, poliza_id: str, cliente_id: str | None, incluir_auditoria: bool = False
    ) -> HistorialPoliza:
        """Devuelve el historial de la póliza ordenado del más reciente al más antiguo.

        Si `cliente_id` no es None, la póliza debe pertenecer a ese cliente (regla del rol
        CLIENTE). Para roles internos de solo lectura se pasa `cliente_id=None` y no se filtra.

        `incluir_auditoria` habilita la vista del analista de cumplimiento (HU25 §19-20): añade
        a los movimientos contractuales el desglose del ajuste de prima y los datos técnicos de
        la solicitud (IP, user-agent, huella). El cliente nunca activa este modo.
        """
        poliza = self._polizas.obtener(poliza_id)
        if poliza is None:
            raise PolizaNoEncontrada(poliza_id)
        if cliente_id is not None and poliza.cliente_id != cliente_id:
            raise AccesoDenegadoHistorial(poliza_id)

        movimientos = self._reunir(poliza, incluir_auditoria)
        # El backend es la fuente de verdad del orden: no se confía en cada repositorio.
        movimientos.sort(key=lambda movimiento: movimiento.fecha, reverse=True)
        return HistorialPoliza(
            poliza_id=poliza.poliza_id,
            numero_poliza=poliza.numero_poliza,
            cliente_id=poliza.cliente_id,
            nombre_ramo=poliza.nombre_ramo,
            estado=poliza.estado_en(hoy_en_colombia(datetime.now(UTC))).value,
            movimientos=movimientos,
        )

    def _reunir(self, poliza: Poliza, incluir_auditoria: bool) -> list[MovimientoPoliza]:
        movimientos: list[MovimientoPoliza] = [movimiento_emision(poliza)]

        cancelacion = movimiento_cancelacion(poliza)
        if cancelacion is not None:
            movimientos.append(cancelacion)

        movimientos.extend(self._movimientos_pagos(poliza))
        movimientos.extend(self._movimientos_endosos(poliza, incluir_auditoria))
        movimientos.extend(self._movimientos_desembolsos(poliza))
        return movimientos

    def _movimientos_pagos(self, poliza: Poliza) -> list[MovimientoPoliza]:
        if poliza.cotizacion_id is None:
            return []
        pagos = self._pagos.listar_por_cotizacion(poliza.cotizacion_id)
        return [movimiento_pago(pago, poliza.poliza_id) for pago in pagos]

    def _movimientos_endosos(
        self, poliza: Poliza, incluir_auditoria: bool
    ) -> list[MovimientoPoliza]:
        return [
            movimiento_endoso(e, incluir_auditoria)
            for e in self._endosos.listar_por_poliza(poliza.poliza_id)
        ]

    def _movimientos_desembolsos(self, poliza: Poliza) -> list[MovimientoPoliza]:
        return [
            movimiento_desembolso(d)
            for d in self._desembolsos.listar_por_poliza(poliza.poliza_id)
            if d.estado in ESTADOS_DESEMBOLSO_VISIBLES
        ]
