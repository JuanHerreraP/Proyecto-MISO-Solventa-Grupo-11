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

/** Si el pago fue una compra o la renovación de una póliza (HU21). */
enum class ConceptoPago {
    COMPRA,
    RENOVACION;

    companion object {
        fun desdeCodigoApi(codigo: String?): ConceptoPago =
            entries.firstOrNull { it.name == codigo } ?: COMPRA
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
    val referenciaPasarela: String? = null,
    val concepto: ConceptoPago = ConceptoPago.COMPRA
)

/** Lo que el cliente debe pagar o firmar para mantener su cobertura (HU21). */
enum class TipoPrimaPendiente {
    RENOVACION,
    COTIZACION,
    FIRMA_PENDIENTE
}

/**
 * Una prima pendiente. Una cotización aún no tiene número de póliza: se muestra con su ramo y
 * el número de cotización. [FIRMA_PENDIENTE] no se paga: el contrato se firma en el portal web.
 */
data class PrimaPendiente(
    val tipo: TipoPrimaPendiente,
    val referenciaId: String,
    val cotizacionId: String,
    val polizaId: String?,
    val numeroPoliza: String?,
    val nombreRamo: String,
    val monto: BigDecimal,
    val moneda: String,
    /** Fecha límite en ISO 8601; null cuando no hay nada que pagar. */
    val fechaLimite: String?,
    val mensaje: String?
) {
    val sePaga: Boolean get() = tipo != TipoPrimaPendiente.FIRMA_PENDIENTE
}

/** Comprobante de un pago aprobado, para mostrar en pantalla (HU21). */
data class ComprobantePago(
    val numero: String,
    val pagoId: String,
    val concepto: ConceptoPago,
    val descripcion: String,
    val polizaId: String?,
    val numeroPoliza: String?,
    val monto: BigDecimal,
    val moneda: String,
    val metodo: MetodoPago,
    val referenciaPasarela: String?,
    /** Cuándo se pagó, en ISO 8601. */
    val pagadoEn: String
)

/** Datos que la UI entrega para solicitar el recaudo. */
data class SolicitudPago(
    val cotizacionId: String,
    val metodo: MetodoPago,
    val tokenTarjeta: String? = null,
    val codigoBanco: String? = null,
    val urlRetorno: String? = null
)
