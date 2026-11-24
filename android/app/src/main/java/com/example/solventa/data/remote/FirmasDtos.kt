package com.example.solventa.data.remote

import com.example.solventa.domain.firmas.ContratoFirma
import com.example.solventa.domain.firmas.ProcesoFirma
import com.google.gson.annotations.SerializedName

data class SolicitudOtpDto(val canal: String = "SMS")

data class SolicitudFirmaDto(
    val codigo: String,
    @SerializedName("huella_documento") val huellaDocumento: String
)

data class CoberturaFirmaDto(
    val nombre: String?,
    @SerializedName("suma_asegurada") val sumaAsegurada: String?
)

data class ContratoFirmaDto(
    @SerializedName("nombre_ramo") val nombreRamo: String?,
    @SerializedName("cobertura_principal") val coberturaPrincipal: CoberturaFirmaDto?,
    @SerializedName("prima_total") val primaTotal: String?,
    val moneda: String?,
    val clausulas: List<String>?,
    @SerializedName("exclusiones_principales") val exclusionesPrincipales: List<String>?
) {
    fun aDominio(): ContratoFirma? {
        val cobertura = coberturaPrincipal ?: return null
        return ContratoFirma(
            nombreRamo = nombreRamo?.takeIf(String::isNotBlank) ?: return null,
            coberturaPrincipal = cobertura.nombre?.takeIf(String::isNotBlank) ?: return null,
            sumaAsegurada = cobertura.sumaAsegurada?.toBigDecimalOrNull() ?: return null,
            primaTotal = primaTotal?.toBigDecimalOrNull() ?: return null,
            moneda = moneda?.takeIf(String::isNotBlank) ?: return null,
            clausulas = clausulas.orEmpty().filter(String::isNotBlank),
            exclusionesPrincipales = exclusionesPrincipales.orEmpty().filter(String::isNotBlank)
        )
    }
}

data class FirmaDto(
    @SerializedName("cotizacion_id") val cotizacionId: String?,
    val estado: String?,
    val contrato: ContratoFirmaDto?,
    @SerializedName("huella_documento") val huellaDocumento: String?,
    @SerializedName("otp_destino") val otpDestino: String?,
    @SerializedName("poliza_id") val polizaId: String?
) {
    fun aDominio(): ProcesoFirma? {
        return ProcesoFirma(
            cotizacionId = cotizacionId?.takeIf(String::isNotBlank) ?: return null,
            estado = estado?.takeIf(String::isNotBlank) ?: return null,
            contrato = contrato?.aDominio() ?: return null,
            huellaDocumento = huellaDocumento?.takeIf { it.matches(Regex("[0-9a-f]{64}")) }
                ?: return null,
            otpDestino = otpDestino,
            polizaId = polizaId
        )
    }
}
