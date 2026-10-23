package com.example.solventa.data.remote

import com.example.solventa.domain.cotizaciones.CoberturaCotizacion
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.example.solventa.domain.cotizaciones.ResultadoCotizacion
import com.google.gson.annotations.SerializedName
import java.math.BigDecimal

data class SolicitudCotizacionDto(
    @SerializedName("cliente_id") val clienteId: String,
    @SerializedName("ramo") val ramo: String,
    @SerializedName("datos_riesgo") val datosRiesgo: Map<String, Any>
)

data class CotizacionDto(
    @SerializedName("cotizacion_id") val cotizacionId: String?,
    @SerializedName("ramo") val ramo: String?,
    @SerializedName("estado") val estado: String?,
    @SerializedName("prima_total") val primaTotal: String?,
    @SerializedName("moneda") val moneda: String?,
    @SerializedName("cobertura_principal") val coberturaPrincipal: CoberturaCotizacionDto?,
    @SerializedName("vigente_hasta") val vigenteHasta: String?,
    @SerializedName("perfil_riesgo_id") val perfilRiesgoId: String?
) {
    fun aResultado(): ResultadoCotizacion? {
        val ramoDominio = ramo?.let(RamoCotizacion::desdeCodigoApi) ?: return null
        val cobertura = coberturaPrincipal?.aDominio() ?: return null
        return ResultadoCotizacion(
            cotizacionId = cotizacionId?.takeIf(String::isNotBlank) ?: return null,
            ramo = ramoDominio,
            estado = estado?.takeIf(String::isNotBlank) ?: return null,
            primaTotal = primaTotal.aDecimalPositivo() ?: return null,
            moneda = moneda?.takeIf(String::isNotBlank) ?: return null,
            coberturaPrincipal = cobertura,
            vigenteHasta = vigenteHasta?.takeIf(String::isNotBlank) ?: return null,
            perfilRiesgoId = perfilRiesgoId
        )
    }
}

data class CoberturaCotizacionDto(
    @SerializedName("codigo") val codigo: String?,
    @SerializedName("nombre") val nombre: String?,
    @SerializedName("suma_asegurada") val sumaAsegurada: String?,
    @SerializedName("descripcion") val descripcion: String?
) {
    fun aDominio(): CoberturaCotizacion? {
        val cod = codigo?.takeIf(String::isNotBlank) ?: return null
        val nom = nombre?.takeIf(String::isNotBlank) ?: return null
        val suma = sumaAsegurada.aDecimalPositivo() ?: return null
        return CoberturaCotizacion(
            codigo = cod,
            nombre = nom,
            sumaAsegurada = suma,
            descripcion = descripcion
        )
    }
}

private fun String?.aDecimalPositivo(): BigDecimal? =
    this?.toBigDecimalOrNull()?.takeIf { it > BigDecimal.ZERO }

