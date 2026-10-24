package com.example.solventa.data.remote

import com.example.solventa.domain.pagos.EstadoPago
import com.example.solventa.domain.pagos.MetodoPago
import com.example.solventa.domain.pagos.Pago
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
    @SerializedName("referencia_pasarela") val referenciaPasarela: String?
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
            referenciaPasarela = referenciaPasarela
        )
    }
}
