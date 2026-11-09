package com.example.solventa.data.remote

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.Billetera
import com.example.solventa.domain.polizas.Certificado
import com.example.solventa.domain.polizas.DocumentoPoliza
import com.example.solventa.domain.polizas.EnlaceCompartido
import com.example.solventa.domain.polizas.HistorialPoliza
import com.example.solventa.domain.polizas.PolizasGateway
import com.google.gson.JsonParseException
import com.google.gson.stream.MalformedJsonException
import java.io.IOException
import java.security.MessageDigest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.Response

class RemotePolizasGateway(private val api: PolizasApi) : PolizasGateway {

    override suspend fun billetera(accessToken: String): ResultadoApi<Billetera> =
        llamar({ api.billetera(bearer(accessToken)) }) { it.aBilletera() }

    override suspend fun certificado(accessToken: String, polizaId: String): ResultadoApi<Certificado> =
        llamar({ api.certificado(bearer(accessToken), polizaId) }) { it.aCertificado() }

    override suspend fun historialPoliza(
        accessToken: String,
        polizaId: String
    ): ResultadoApi<HistorialPoliza> =
        llamar({ api.historialPoliza(bearer(accessToken), polizaId) }) { it.aHistorial() }

    override suspend fun documento(
        accessToken: String,
        polizaId: String
    ): ResultadoApi<DocumentoPoliza> = withContext(Dispatchers.IO) {
        try {
            val respuesta = api.documento(bearer(accessToken), polizaId)
            if (!respuesta.isSuccessful) {
                val (codigo, mensaje) = RemoteAuthGateway.leerError(respuesta.errorBody()?.string())
                ResultadoApi.Fallo(respuesta.code(), codigo, mensaje)
            } else {
                val cuerpo = respuesta.body()
                val longitud = cuerpo?.contentLength() ?: -1L
                if (cuerpo == null || longitud > MAXIMO_PDF_BYTES) {
                    ResultadoApi.Fallo(CUERPO_INVALIDO, null, null)
                } else {
                    val contenido = cuerpo.bytes()
                    val huella = respuesta.headers()["X-Huella-Documento"]
                    if (
                        contenido.size > MAXIMO_PDF_BYTES ||
                        !contenido.esPdf() ||
                        !contenido.coincideCon(huella)
                    ) {
                        ResultadoApi.Fallo(CUERPO_INVALIDO, null, null)
                    } else {
                        ResultadoApi.Exito(
                            DocumentoPoliza(
                                nombreArchivo = nombreArchivo(
                                    respuesta.headers()["Content-Disposition"],
                                    polizaId
                                ),
                                contenido = contenido,
                                huellaSha256 = huella!!
                            )
                        )
                    }
                }
            }
        } catch (error: IOException) {
            ResultadoApi.SinConexion
        }
    }

    override suspend fun compartir(accessToken: String, polizaId: String): ResultadoApi<EnlaceCompartido> =
        llamar({ api.compartir(bearer(accessToken), polizaId) }) { it.aEnlace() }

    private fun bearer(accessToken: String) = "Bearer $accessToken"

    /** Un cuerpo exitoso que no se puede mapear se trata como fallo, sin romper la UI. */
    private suspend fun <D : Any, T : Any> llamar(
        peticion: suspend () -> Response<D>,
        mapear: (D) -> T?
    ): ResultadoApi<T> = try {
        val respuesta = peticion()
        val cuerpo = respuesta.body()
        if (respuesta.isSuccessful) {
            val valor = cuerpo?.let(mapear)
            if (valor != null) ResultadoApi.Exito(valor) else ResultadoApi.Fallo(respuesta.code(), null, null)
        } else {
            val (codigo, mensaje) = RemoteAuthGateway.leerError(respuesta.errorBody()?.string())
            ResultadoApi.Fallo(respuesta.code(), codigo, mensaje)
        }
    } catch (error: MalformedJsonException) {
        // Respondió algo que no es JSON (por ejemplo, la página de un proxy): no es falta de red.
        ResultadoApi.Fallo(CUERPO_INVALIDO, null, null)
    } catch (error: IOException) {
        ResultadoApi.SinConexion
    } catch (error: JsonParseException) {
        ResultadoApi.Fallo(CUERPO_INVALIDO, null, null)
    }

    private companion object {
        /** Código para respuestas que no se pudieron leer; no coincide con ningún HTTP real. */
        const val CUERPO_INVALIDO = 0
        const val MAXIMO_PDF_BYTES = 10 * 1024 * 1024

        fun ByteArray.esPdf(): Boolean =
            size >= 5 && copyOfRange(0, 5).contentEquals("%PDF-".toByteArray())

        fun ByteArray.coincideCon(huella: String?): Boolean {
            if (huella == null || !huella.matches(Regex("^[0-9a-fA-F]{64}$"))) return false
            val esperada = huella.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
            val calculada = MessageDigest.getInstance("SHA-256").digest(this)
            return MessageDigest.isEqual(calculada, esperada)
        }

        fun nombreArchivo(disposicion: String?, polizaId: String): String {
            val recibido = disposicion
                ?.substringAfter("filename=", "")
                ?.trim()
                ?.trim('"')
                ?.substringAfterLast('/')
                ?.substringAfterLast('\\')
                ?.takeIf { it.endsWith(".pdf", ignoreCase = true) }
            return recibido ?: "poliza-$polizaId.pdf"
        }
    }
}
