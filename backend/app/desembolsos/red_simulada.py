"""Red de desembolsos simulada para desarrollo (sustituible por el proveedor real, EC06).

Determinista según los últimos cuatro dígitos de la cuenta, para probar los tres desenlaces:
- termina en 0000 -> FALLIDA (CUENTA_INEXISTENTE)
- termina en 9999 -> RedNoDisponible: el desembolso queda PENDIENTE para reintentar
- cualquier otra  -> COMPLETADA
El código de retiro siempre se emite. La misma referencia devuelve la misma transacción.
"""

import hashlib

from app.desembolsos.modelos import EstadoDesembolso, TipoCuenta
from app.desembolsos.puertos import (
    OrdenRetiro,
    RedNoDisponible,
    ResultadoDesembolso,
    Transferencia,
)


def _huella(*partes: str) -> str:
    return hashlib.sha256("|".join(partes).encode()).hexdigest()


class RedDesembolsosSimulada:
    def tokenizar_cuenta(self, codigo_banco: str, tipo: TipoCuenta, numero: str) -> str:
        # El token lleva los últimos dígitos, como hacen muchas redes, y nada más del número.
        return f"CTA-{_huella(codigo_banco, tipo.value, numero)[:16]}-{numero[-4:]}"

    def transferir(self, transferencia: Transferencia) -> ResultadoDesembolso:
        ultimos = transferencia.token_cuenta[-4:]
        if ultimos == "9999":
            raise RedNoDisponible("tiempo de espera agotado")
        referencia = "TRF-" + _huella(transferencia.referencia_interna)[:16].upper()
        if ultimos == "0000":
            return ResultadoDesembolso(
                referencia_transaccion=referencia,
                estado=EstadoDesembolso.FALLIDA,
                motivo_fallo="CUENTA_INEXISTENTE",
            )
        return ResultadoDesembolso(
            referencia_transaccion=referencia, estado=EstadoDesembolso.COMPLETADA
        )

    def emitir_codigo_retiro(self, orden: OrdenRetiro) -> ResultadoDesembolso:
        huella = _huella("retiro", orden.referencia_interna)
        codigo = str(int(huella[:12], 16) % 10**8).zfill(8)
        return ResultadoDesembolso(
            referencia_transaccion="RET-" + huella[12:28].upper(),
            estado=EstadoDesembolso.COMPLETADA,
            codigo_retiro=codigo,
        )
