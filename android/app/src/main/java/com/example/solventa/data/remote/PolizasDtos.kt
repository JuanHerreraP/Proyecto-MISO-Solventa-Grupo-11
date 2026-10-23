package com.example.solventa.data.remote

import com.example.solventa.domain.polizas.Billetera
import com.example.solventa.domain.polizas.Certificado
import com.example.solventa.domain.polizas.EnlaceCompartido
import com.example.solventa.domain.polizas.EstadoPoliza
import com.example.solventa.domain.polizas.PolizaResumen
import com.google.gson.annotations.SerializedName

/**
 * Gson no pasa por el constructor de Kotlin: un campo ausente llega como null aunque el tipo
 * no lo permita. Por eso los DTO son anulables y el mapeo descarta lo incompleto.
 */
data class PolizaEnBilleteraDto(
    @SerializedName("poliza_id") val polizaId: String?,
    @SerializedName("numero_poliza") val numeroPoliza: String?,
    @SerializedName("ramo") val ramo: String?,
    @SerializedName("nombre_ramo") val nombreRamo: String?,
    @SerializedName("estado") val estado: String?,
    @SerializedName("activa") val activa: Boolean?,
    @SerializedName("fecha_inicio") val fechaInicio: String?,
    @SerializedName("fecha_fin") val fechaFin: String?,
    @SerializedName("cobertura_principal") val coberturaPrincipal: String?
) {
    fun aPoliza(): PolizaResumen? {
        val estadoPoliza = estado.aEstado() ?: return null
        return PolizaResumen(
            polizaId = polizaId ?: return null,
            numeroPoliza = numeroPoliza ?: return null,
            ramo = ramo.orEmpty(),
            nombreRamo = nombreRamo ?: ramo.orEmpty(),
            estado = estadoPoliza,
            activa = activa ?: (estadoPoliza == EstadoPoliza.VIGENTE),
            fechaInicio = fechaInicio ?: return null,
            fechaFin = fechaFin ?: return null,
            coberturaPrincipal = coberturaPrincipal.orEmpty()
        )
    }
}

data class BilleteraDto(
    @SerializedName("polizas") val polizas: List<PolizaEnBilleteraDto>?,
    @SerializedName("total_vigentes") val totalVigentes: Int?,
    @SerializedName("total_inactivas") val totalInactivas: Int?
) {
    fun aBilletera(): Billetera {
        val lista = polizas.orEmpty().mapNotNull { it.aPoliza() }
        return Billetera(
            polizas = lista,
            totalVigentes = lista.count { it.activa },
            totalInactivas = lista.count { !it.activa }
        )
    }
}

data class CertificadoDto(
    @SerializedName("poliza_id") val polizaId: String?,
    @SerializedName("numero_poliza") val numeroPoliza: String?,
    @SerializedName("nombre_ramo") val nombreRamo: String?,
    @SerializedName("estado") val estado: String?,
    @SerializedName("activa") val activa: Boolean?,
    @SerializedName("titular") val titular: String?,
    @SerializedName("documento_titular") val documentoTitular: String?,
    @SerializedName("fecha_inicio") val fechaInicio: String?,
    @SerializedName("fecha_fin") val fechaFin: String?,
    @SerializedName("cobertura_principal") val coberturaPrincipal: String?,
    @SerializedName("suma_asegurada") val sumaAsegurada: String?,
    @SerializedName("moneda") val moneda: String?,
    @SerializedName("contenido_qr") val contenidoQr: String?
) {
    fun aCertificado(): Certificado? {
        val estadoPoliza = estado.aEstado() ?: return null
        return Certificado(
            polizaId = polizaId ?: return null,
            numeroPoliza = numeroPoliza ?: return null,
            nombreRamo = nombreRamo.orEmpty(),
            estado = estadoPoliza,
            activa = activa ?: (estadoPoliza == EstadoPoliza.VIGENTE),
            titular = titular.orEmpty(),
            documentoTitular = documentoTitular.orEmpty(),
            fechaInicio = fechaInicio ?: return null,
            fechaFin = fechaFin ?: return null,
            coberturaPrincipal = coberturaPrincipal.orEmpty(),
            sumaAsegurada = sumaAsegurada.orEmpty(),
            moneda = moneda ?: "COP",
            contenidoQr = contenidoQr ?: return null
        )
    }
}

data class EnlaceCompartidoDto(
    @SerializedName("url") val url: String?,
    @SerializedName("expira_en") val expiraEn: String?
) {
    fun aEnlace(): EnlaceCompartido? {
        val direccion = url?.takeIf { it.startsWith("https://") || it.startsWith("http://") }
            ?: return null
        return EnlaceCompartido(url = direccion, expiraEn = expiraEn.orEmpty())
    }
}

private fun String?.aEstado(): EstadoPoliza? =
    this?.let { valor -> EstadoPoliza.entries.firstOrNull { it.name == valor } }
