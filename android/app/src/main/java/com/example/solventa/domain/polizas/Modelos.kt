package com.example.solventa.domain.polizas

import com.example.solventa.domain.auth.ResultadoApi

/** Estado que el backend calcula para la billetera (HU07). */
enum class EstadoPoliza { VIGENTE, VENCIDA, CANCELADA }

/** Lo que la billetera muestra de cada póliza. Las fechas llegan en ISO (aaaa-mm-dd). */
data class PolizaResumen(
    val polizaId: String,
    val numeroPoliza: String,
    val ramo: String,
    val nombreRamo: String,
    val estado: EstadoPoliza,
    val activa: Boolean,
    val fechaInicio: String,
    val fechaFin: String,
    val coberturaPrincipal: String
)

data class Billetera(
    val polizas: List<PolizaResumen>,
    val totalVigentes: Int,
    val totalInactivas: Int
) {
    val vigentes: List<PolizaResumen> get() = polizas.filter { it.activa }
    val inactivas: List<PolizaResumen> get() = polizas.filterNot { it.activa }
    val vacia: Boolean get() = polizas.isEmpty()
}

/** Certificado digital. El documento del titular ya llega enmascarado desde el backend. */
data class Certificado(
    val polizaId: String,
    val numeroPoliza: String,
    val nombreRamo: String,
    val estado: EstadoPoliza,
    val activa: Boolean,
    val titular: String,
    val documentoTitular: String,
    val fechaInicio: String,
    val fechaFin: String,
    val coberturaPrincipal: String,
    val sumaAsegurada: String,
    val moneda: String,
    val contenidoQr: String
)

/** Enlace temporal para compartir el certificado. [expiraEn] llega en ISO 8601. */
data class EnlaceCompartido(
    val url: String,
    val expiraEn: String
)

/** Puerto hacia el backend de la billetera. */
interface PolizasGateway {
    suspend fun billetera(accessToken: String): ResultadoApi<Billetera>
    suspend fun certificado(accessToken: String, polizaId: String): ResultadoApi<Certificado>
    suspend fun compartir(accessToken: String, polizaId: String): ResultadoApi<EnlaceCompartido>
}

/**
 * Entrega el access token de la sesión activa sin exponerlo a la UI. Lo implementa el
 * coordinador de autenticación, que es el único que guarda los tokens.
 */
interface SesionAutenticada {
    /** Null si no hay sesión o si el token ya venció. */
    fun accessTokenVigente(): String?

    /** El backend rechazó el token: la sesión se cierra en memoria. */
    fun sesionRechazada()
}
