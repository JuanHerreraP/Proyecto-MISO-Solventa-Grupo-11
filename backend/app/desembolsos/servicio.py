"""Casos de uso del desembolso de indemnizaciones (HU15 / BPM-65).

- Al aprobarse un siniestro se ordena el pago: a la cuenta registrada del cliente o, si no la
  tiene, con un código de retiro.
- Idempotente: hay un único desembolso por siniestro (restricción única). Repetir la orden,
  un doble clic o dos aprobaciones simultáneas devuelven el mismo desembolso, y cada intento
  usa una referencia estable frente a la red, así que no se paga dos veces.
- Si la red no responde, el desembolso queda PENDIENTE y se reintenta con la misma
  referencia. Si la transferencia FALLA (cuenta inexistente), Operaciones puede reintentar
  con un intento nuevo, por ejemplo cuando el cliente corrige su cuenta.
"""

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from app.desembolsos.modelos import (
    CuentaDesembolso,
    Desembolso,
    EstadoDesembolso,
    MedioDesembolso,
    SolicitudCuenta,
)
from app.desembolsos.puertos import (
    OrdenRetiro,
    RedDesembolsos,
    RedNoDisponible,
    RepositorioCuentas,
    RepositorioDesembolsos,
    Transferencia,
)
from app.siniestros.modelos import EstadoSiniestro, Siniestro

logger = logging.getLogger(__name__)

MOTIVO_RED_NO_DISPONIBLE = "RED_NO_DISPONIBLE"


class SiniestroNoAprobado(Exception):
    """Solo se desembolsa un siniestro aprobado con monto."""


class DesembolsoNoEncontrado(Exception):
    pass


class DesembolsoNoReintentable(Exception):
    """El desembolso ya se completó: no hay nada que reintentar."""


class ServicioDesembolsos:
    def __init__(
        self,
        desembolsos: RepositorioDesembolsos,
        cuentas: RepositorioCuentas,
        red: RedDesembolsos,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        generar_id: Callable[[], str] = lambda: f"DES-{uuid.uuid4()}",
    ):
        self._desembolsos = desembolsos
        self._cuentas = cuentas
        self._red = red
        self._reloj = reloj
        self._generar_id = generar_id

    # --- Cuenta del cliente --------------------------------------------------------------

    def registrar_cuenta(self, cliente_id: str, solicitud: SolicitudCuenta) -> CuentaDesembolso:
        """Tokeniza la cuenta en la red; el número completo no se guarda en Solventa."""
        token = self._red.tokenizar_cuenta(
            solicitud.codigo_banco, solicitud.tipo_cuenta, solicitud.numero_cuenta
        )
        ahora = self._reloj()
        anterior = self._cuentas.obtener(cliente_id)
        cuenta = CuentaDesembolso(
            cliente_id=cliente_id,
            codigo_banco=solicitud.codigo_banco,
            tipo_cuenta=solicitud.tipo_cuenta,
            ultimos_digitos=solicitud.numero_cuenta[-4:],
            token_cuenta=token,
            registrada_en=anterior.registrada_en if anterior else ahora,
            actualizada_en=ahora,
        )
        self._cuentas.guardar(cuenta)
        return cuenta

    def cuenta(self, cliente_id: str) -> CuentaDesembolso | None:
        return self._cuentas.obtener(cliente_id)

    # --- Desembolso ----------------------------------------------------------------------

    def desembolsar(self, siniestro: Siniestro) -> Desembolso:
        """Ordena el pago del siniestro aprobado. Repetirla devuelve el mismo desembolso."""
        if siniestro.estado is not EstadoSiniestro.APROBADO or siniestro.monto_aprobado is None:
            raise SiniestroNoAprobado(siniestro.siniestro_id)

        existente = self._desembolsos.obtener_por_siniestro(siniestro.siniestro_id)
        if existente is not None:
            if existente.estado is EstadoDesembolso.PENDIENTE:
                # Un intento quedó sin respuesta de la red: se repite con la misma referencia.
                return self._ejecutar(existente)
            return existente

        ahora = self._reloj()
        cuenta = self._cuentas.obtener(siniestro.cliente_id)
        nuevo = Desembolso(
            desembolso_id=self._generar_id(),
            siniestro_id=siniestro.siniestro_id,
            poliza_id=siniestro.poliza_id,
            cliente_id=siniestro.cliente_id,
            monto=siniestro.monto_aprobado,
            moneda=siniestro.moneda,
            creado_en=ahora,
            actualizado_en=ahora,
            **self._medio(cuenta),
        )
        if not self._desembolsos.crear(nuevo):
            # Otra petición creó el desembolso de este siniestro al mismo tiempo.
            ganador = self._desembolsos.obtener_por_siniestro(siniestro.siniestro_id)
            if ganador is None:
                raise DesembolsoNoEncontrado(siniestro.siniestro_id)
            return ganador
        return self._ejecutar(nuevo)

    def reintentar(self, siniestro_id: str) -> Desembolso:
        desembolso = self._desembolsos.obtener_por_siniestro(siniestro_id)
        if desembolso is None:
            raise DesembolsoNoEncontrado(siniestro_id)
        if desembolso.estado is EstadoDesembolso.COMPLETADA:
            raise DesembolsoNoReintentable(siniestro_id)
        if desembolso.estado is EstadoDesembolso.FALLIDA:
            # Intento nuevo (referencia nueva) con la cuenta que el cliente tenga hoy.
            cuenta = self._cuentas.obtener(desembolso.cliente_id)
            desembolso = desembolso.model_copy(
                update={
                    "intento": desembolso.intento + 1,
                    "estado": EstadoDesembolso.PENDIENTE,
                    "referencia_transaccion": None,
                    "motivo_fallo": None,
                    **self._medio(cuenta),
                }
            )
        return self._ejecutar(desembolso)

    def obtener_por_siniestro(self, siniestro_id: str) -> Desembolso | None:
        return self._desembolsos.obtener_por_siniestro(siniestro_id)

    def listar_de_cliente(self, cliente_id: str) -> list[Desembolso]:
        return self._desembolsos.listar_por_cliente(cliente_id)

    # --- Internos ------------------------------------------------------------------------

    @staticmethod
    def _medio(cuenta: CuentaDesembolso | None) -> dict[str, object]:
        if cuenta is None:
            return {"medio": MedioDesembolso.CODIGO_RETIRO, "destino": "Código de retiro"}
        return {"medio": MedioDesembolso.CUENTA_BANCARIA, "destino": cuenta.enmascarada}

    def _ejecutar(self, desembolso: Desembolso) -> Desembolso:
        try:
            if desembolso.medio is MedioDesembolso.CUENTA_BANCARIA:
                cuenta = self._cuentas.obtener(desembolso.cliente_id)
                if cuenta is None:
                    # El cliente retiró su cuenta: se paga con código de retiro.
                    desembolso = desembolso.model_copy(update=self._medio(None))
                    return self._ejecutar(desembolso)
                resultado = self._red.transferir(
                    Transferencia(
                        referencia_interna=desembolso.referencia_interna,
                        monto=desembolso.monto,
                        moneda=desembolso.moneda,
                        token_cuenta=cuenta.token_cuenta,
                    )
                )
            else:
                resultado = self._red.emitir_codigo_retiro(
                    OrdenRetiro(
                        referencia_interna=desembolso.referencia_interna,
                        monto=desembolso.monto,
                        moneda=desembolso.moneda,
                    )
                )
        except RedNoDisponible:
            logger.warning(
                "La red de desembolsos no respondió para %s; queda pendiente",
                desembolso.desembolso_id,
            )
            pendiente = desembolso.model_copy(
                update={
                    "estado": EstadoDesembolso.PENDIENTE,
                    "motivo_fallo": MOTIVO_RED_NO_DISPONIBLE,
                    "actualizado_en": self._reloj(),
                }
            )
            self._desembolsos.guardar(pendiente)
            return pendiente

        ahora = self._reloj()
        final = desembolso.model_copy(
            update={
                "estado": resultado.estado,
                "referencia_transaccion": resultado.referencia_transaccion,
                "codigo_retiro": resultado.codigo_retiro,
                "motivo_fallo": resultado.motivo_fallo,
                "actualizado_en": ahora,
                "completado_en": ahora if resultado.estado is EstadoDesembolso.COMPLETADA else None,
            }
        )
        self._desembolsos.guardar(final)
        logger.info(
            "Desembolso %s del siniestro %s: %s (%s)",
            final.desembolso_id,
            final.siniestro_id,
            final.estado.value,
            final.referencia_transaccion,
        )
        return final
