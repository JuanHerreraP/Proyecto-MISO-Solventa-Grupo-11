package com.example.solventa.data.remote

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.Billetera
import com.example.solventa.domain.polizas.Certificado
import com.example.solventa.domain.polizas.EnlaceCompartido
import com.example.solventa.domain.polizas.PolizasGateway
import com.google.gson.JsonParseException
import com.google.gson.stream.MalformedJsonException
import java.io.IOException
import retrofit2.Response

class RemotePolizasGateway(private val api: PolizasApi) : PolizasGateway {

    override suspend fun billetera(accessToken: String): ResultadoApi<Billetera> =
        llamar({ api.billetera(bearer(accessToken)) }) { it.aBilletera() }

    override suspend fun certificado(accessToken: String, polizaId: String): ResultadoApi<Certificado> =
        llamar({ api.certificado(bearer(accessToken), polizaId) }) { it.aCertificado() }

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
    }
}
