package com.example.solventa.data.remote

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.notificaciones.Bandeja
import com.example.solventa.domain.notificaciones.NotificacionesGateway
import com.google.gson.JsonParseException
import com.google.gson.stream.MalformedJsonException
import java.io.IOException
import retrofit2.Response

class RemoteNotificacionesGateway(private val api: NotificacionesApi) : NotificacionesGateway {

    override suspend fun listar(accessToken: String): ResultadoApi<Bandeja> =
        llamar({ api.listar(bearer(accessToken)) }) { it.aBandeja() }

    override suspend fun contarNoLeidas(accessToken: String): ResultadoApi<Int> =
        llamar({ api.contarNoLeidas(bearer(accessToken)) }) { it.noLeidas }

    override suspend fun marcarLeida(
        accessToken: String,
        notificacionId: String
    ): ResultadoApi<Int> =
        llamar({ api.marcarLeida(bearer(accessToken), notificacionId) }) { it.noLeidas }

    override suspend fun registrarDispositivo(
        accessToken: String,
        tokenPush: String
    ): ResultadoApi<Unit> = sinCuerpo {
        api.registrarDispositivo(bearer(accessToken), SolicitudDispositivoDto(tokenPush))
    }

    override suspend fun darDeBajaDispositivo(
        accessToken: String,
        tokenPush: String
    ): ResultadoApi<Unit> = sinCuerpo {
        api.darDeBajaDispositivo(bearer(accessToken), BajaDispositivoDto(tokenPush))
    }

    override suspend fun obtenerPreferencia(accessToken: String): ResultadoApi<Boolean> =
        llamar({ api.obtenerPreferencia(bearer(accessToken)) }) { it.pushHabilitado }

    override suspend fun cambiarPreferencia(
        accessToken: String,
        pushHabilitado: Boolean
    ): ResultadoApi<Boolean> = llamar(
        { api.cambiarPreferencia(bearer(accessToken), PreferenciaPushDto(pushHabilitado)) }
    ) { it.pushHabilitado }

    private fun bearer(accessToken: String) = "Bearer $accessToken"

    /** Un cuerpo exitoso que no se puede mapear se trata como fallo, sin romper la UI. */
    private suspend fun <D : Any, T : Any> llamar(
        peticion: suspend () -> Response<D>,
        mapear: (D) -> T?
    ): ResultadoApi<T> = ejecutar {
        val respuesta = peticion()
        if (respuesta.isSuccessful) {
            val valor = respuesta.body()?.let(mapear)
            if (valor != null) {
                ResultadoApi.Exito(valor)
            } else {
                ResultadoApi.Fallo(respuesta.code(), null, null)
            }
        } else {
            respuesta.aFallo()
        }
    }

    /** Para las respuestas 204: no hay cuerpo que mapear. */
    private suspend fun sinCuerpo(peticion: suspend () -> Response<Unit>): ResultadoApi<Unit> =
        ejecutar {
            val respuesta = peticion()
            if (respuesta.isSuccessful) ResultadoApi.Exito(Unit) else respuesta.aFallo()
        }

    private suspend fun <T> ejecutar(operacion: suspend () -> ResultadoApi<T>): ResultadoApi<T> =
        try {
            operacion()
        } catch (error: MalformedJsonException) {
            ResultadoApi.Fallo(CUERPO_INVALIDO, null, null)
        } catch (error: JsonParseException) {
            ResultadoApi.Fallo(CUERPO_INVALIDO, null, null)
        } catch (error: IOException) {
            ResultadoApi.SinConexion
        }

    private fun <T> Response<T>.aFallo(): ResultadoApi.Fallo {
        val (codigo, mensaje) = RemoteAuthGateway.leerError(errorBody()?.string())
        return ResultadoApi.Fallo(code(), codigo, mensaje)
    }

    private companion object {
        /** Código para respuestas que no se pudieron leer; no coincide con ningún HTTP real. */
        const val CUERPO_INVALIDO = 0
    }
}
