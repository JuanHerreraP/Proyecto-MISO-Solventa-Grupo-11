package com.example.solventa.domain.pagos

import java.math.BigDecimal

/** Medios de pago habilitados por Solventa (HU13). */
enum class MetodoPago(val codigoApi: String) {
    TARJETA("TARJETA"),
    PSE("PSE")
}

/** Estados del recaudo que devuelve el backend. */
enum class EstadoPago {
    PENDIENTE,
    APROBADO,
    RECHAZADO;

    companion object {
        fun desdeCodigoApi(codigo: String): EstadoPago? =
            entries.firstOrNull { it.name == codigo }
    }
}

/** Resultado de un intento de recaudo. */
data class Pago(
    val pagoId: String,
    val cotizacionId: String,
    val metodo: MetodoPago,
    val monto: BigDecimal,
    val moneda: String,
    val estado: EstadoPago,
    val motivoRechazo: String? = null,
    val urlRedireccion: String? = null,
    val referenciaPasarela: String? = null
)

/** Datos que la UI entrega para solicitar el recaudo. */
data class SolicitudPago(
    val cotizacionId: String,
    val metodo: MetodoPago,
    val tokenTarjeta: String? = null,
    val codigoBanco: String? = null,
    val urlRetorno: String? = null
)
