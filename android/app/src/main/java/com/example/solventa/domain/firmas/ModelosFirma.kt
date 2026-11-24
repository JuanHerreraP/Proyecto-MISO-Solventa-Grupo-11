package com.example.solventa.domain.firmas

import com.example.solventa.domain.auth.ResultadoApi
import java.math.BigDecimal

/** Condiciones inmutables del contrato que el cliente revisa antes de firmar. */
data class ContratoFirma(
    val nombreRamo: String,
    val coberturaPrincipal: String,
    val sumaAsegurada: BigDecimal,
    val primaTotal: BigDecimal,
    val moneda: String,
    val clausulas: List<String>,
    val exclusionesPrincipales: List<String>
)

data class ProcesoFirma(
    val cotizacionId: String,
    val estado: String,
    val contrato: ContratoFirma,
    val huellaDocumento: String,
    val otpDestino: String?,
    val polizaId: String?
)

data class EstadoFirma(
    val cargando: Boolean = false,
    val enviandoCodigo: Boolean = false,
    val firmando: Boolean = false,
    val proceso: ProcesoFirma? = null,
    val error: String? = null
)

/** Puerto Android hacia los endpoints de firma existentes. */
interface FirmasGateway {
    suspend fun presentar(accessToken: String, cotizacionId: String): ResultadoApi<ProcesoFirma>
    suspend fun solicitarOtp(accessToken: String, cotizacionId: String): ResultadoApi<ProcesoFirma>
    suspend fun firmar(
        accessToken: String,
        cotizacionId: String,
        codigo: String,
        huellaDocumento: String
    ): ResultadoApi<ProcesoFirma>
}

object MensajesFirma {
    const val SIN_CONEXION = "SIN_CONEXION"
    const val CONTRATO_NO_DISPONIBLE = "CONTRATO_NO_DISPONIBLE"
    const val CODIGO_INVALIDO = "CODIGO_INVALIDO"
    const val ERROR_GENERICO = "ERROR_GENERICO"
    const val SESION_VENCIDA = "SESION_VENCIDA"
}
