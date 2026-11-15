package com.example.solventa.data.remote

import com.example.solventa.domain.pagos.ComprobantePago
import com.example.solventa.domain.pagos.ConceptoPago
import com.example.solventa.domain.pagos.EstadoPago
import com.example.solventa.domain.pagos.MetodoPago
import com.example.solventa.domain.pagos.Pago
import com.example.solventa.domain.pagos.PrimaPendiente
import com.example.solventa.domain.pagos.TipoPrimaPendiente
import com.google.gson.annotations.SerializedName
import java.math.BigDecimal

data class SolicitudPagoDto(
    @SerializedName("cotizacion_id") val cotizacionId: String,
    @SerializedName("metodo") val metodo: String,
    @SerializedName("token_tarjeta") val tokenTarjeta: String? = null,
    @SerializedName("codigo_banco") val codigoBanco: String? = null,
    @SerializedName("url_retorno") val urlRetorno: String? = null
)

data class PagoDto(
    @SerializedName("pago_id") val pagoId: String?,
    @SerializedName("cotizacion_id") val cotizacionId: String?,
    @SerializedName("metodo") val metodo: String?,
    @SerializedName("monto") val monto: String?,
    @SerializedName("moneda") val moneda: String?,
    @SerializedName("estado") val estado: String?,
    @SerializedName("motivo_rechazo") val motivoRechazo: String?,
    @SerializedName("url_redireccion") val urlRedireccion: String?,
    @SerializedName("referencia_pasarela") val referenciaPasarela: String?,
    @SerializedName("concepto") val concepto: String? = null
) {
    fun aDominio(): Pago? {
        val estadoDominio = estado?.let(EstadoPago::desdeCodigoApi) ?: return null
        val metodoDominio = MetodoPago.entries.firstOrNull { it.codigoApi == metodo } ?: return null
        return Pago(
            pagoId = pagoId?.takeIf(String::isNotBlank) ?: return null,
            cotizacionId = cotizacionId?.takeIf(String::isNotBlank) ?: return null,
            metodo = metodoDominio,
            monto = monto?.toBigDecimalOrNull()?.takeIf { it > BigDecimal.ZERO } ?: return null,
            moneda = moneda?.takeIf(String::isNotBlank) ?: return null,
            estado = estadoDominio,
            motivoRechazo = motivoRechazo,
            urlRedireccion = urlRedireccion,
            referenciaPasarela = referenciaPasarela,
            concepto = ConceptoPago.desdeCodigoApi(concepto)
        )
    }
}

data class PrimaPendienteDto(
    @SerializedName("tipo") val tipo: String?,
    @SerializedName("referencia_id") val referenciaId: String?,
    @SerializedName("cotizacion_id") val cotizacionId: String?,
    @SerializedName("poliza_id") val polizaId: String?,
    @SerializedName("numero_poliza") val numeroPoliza: String?,
    @SerializedName("nombre_ramo") val nombreRamo: String?,
    @SerializedName("monto") val monto: String?,
    @SerializedName("moneda") val moneda: String?,
    @SerializedName("fecha_limite") val fechaLimite: String?,
    @SerializedName("mensaje") val mensaje: String?
) {
    fun aDominio(): PrimaPendiente? {
        val tipoDominio = TipoPrimaPendiente.entries.firstOrNull { it.name == tipo } ?: return null
        return PrimaPendiente(
            tipo = tipoDominio,
            referenciaId = referenciaId?.takeIf(String::isNotBlank) ?: return null,
            cotizacionId = cotizacionId?.takeIf(String::isNotBlank) ?: return null,
            polizaId = polizaId,
            numeroPoliza = numeroPoliza,
            nombreRamo = nombreRamo.orEmpty(),
            monto = monto?.toBigDecimalOrNull()?.takeIf { it > BigDecimal.ZERO } ?: return null,
            moneda = moneda?.takeIf(String::isNotBlank) ?: return null,
            fechaLimite = fechaLimite,
            mensaje = mensaje
        )
    }
}

data class PrimasPendientesDto(
    @SerializedName("primas") val primas: List<PrimaPendienteDto>?
)

data class ComprobanteDto(
    @SerializedName("numero") val numero: String?,
    @SerializedName("pago_id") val pagoId: String?,
    @SerializedName("concepto") val concepto: String?,
    @SerializedName("descripcion") val descripcion: String?,
    @SerializedName("poliza_id") val polizaId: String?,
    @SerializedName("numero_poliza") val numeroPoliza: String?,
    @SerializedName("monto") val monto: String?,
    @SerializedName("moneda") val moneda: String?,
    @SerializedName("metodo") val metodo: String?,
    @SerializedName("referencia_pasarela") val referenciaPasarela: String?,
    @SerializedName("pagado_en") val pagadoEn: String?
) {
    fun aDominio(): ComprobantePago? {
        val metodoDominio = MetodoPago.entries.firstOrNull { it.codigoApi == metodo } ?: return null
        return ComprobantePago(
            numero = numero?.takeIf(String::isNotBlank) ?: return null,
            pagoId = pagoId?.takeIf(String::isNotBlank) ?: return null,
            concepto = ConceptoPago.desdeCodigoApi(concepto),
            descripcion = descripcion.orEmpty(),
            polizaId = polizaId,
            numeroPoliza = numeroPoliza,
            monto = monto?.toBigDecimalOrNull()?.takeIf { it > BigDecimal.ZERO } ?: return null,
            moneda = moneda?.takeIf(String::isNotBlank) ?: return null,
            metodo = metodoDominio,
            referenciaPasarela = referenciaPasarela,
            pagadoEn = pagadoEn.orEmpty()
        )
    }
}
