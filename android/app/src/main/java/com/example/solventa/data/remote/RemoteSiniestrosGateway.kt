package com.example.solventa.data.remote

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.siniestros.Siniestro
import com.example.solventa.domain.siniestros.Siniestros
import com.example.solventa.domain.siniestros.SiniestrosGateway
import com.example.solventa.domain.siniestros.SolicitudSiniestro
import com.google.gson.JsonParseException
import com.google.gson.stream.MalformedJsonException
import java.io.IOException
import retrofit2.Response

class RemoteSiniestrosGateway(private val api: SiniestrosApi) : SiniestrosGateway {

    override suspend fun listar(accessToken: String): ResultadoApi<Siniestros> =
        llamar({ api.listar(bearer(accessToken)) }) { it.aSiniestros() }

    override suspend fun registrar(
        accessToken: String,
        solicitud: SolicitudSiniestro
    ): ResultadoApi<Siniestro> =
        llamar({ api.registrar(bearer(accessToken), solicitud.aDto()) }) { it.aSiniestro() }

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
