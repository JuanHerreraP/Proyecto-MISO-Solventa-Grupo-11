package com.example.solventa.data.remote

import com.example.solventa.domain.auth.AuthGateway
import com.example.solventa.domain.auth.Perfil
import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.auth.Tokens
import com.example.solventa.domain.auth.mapear
import com.google.gson.JsonParser
import java.io.IOException
import retrofit2.Response

class RemoteAuthGateway(private val api: AuthApi) : AuthGateway {

    override suspend fun login(email: String, password: String): ResultadoApi<Tokens> =
        llamar { api.login(SolicitudLoginDto(email, password)) }.mapear { it.aTokens() }

    override suspend fun renovar(refreshToken: String): ResultadoApi<Tokens> =
        llamar { api.renovar(SolicitudRefreshDto(refreshToken)) }.mapear { it.aTokens() }

    override suspend fun cerrarSesion(refreshToken: String): ResultadoApi<Unit> = try {
        val respuesta = api.cerrarSesion(SolicitudRefreshDto(refreshToken))
        if (respuesta.isSuccessful) ResultadoApi.Exito(Unit) else fallo(respuesta)
    } catch (error: IOException) {
        ResultadoApi.SinConexion
    }

    override suspend fun perfil(accessToken: String): ResultadoApi<Perfil> =
        llamar { api.perfil("Bearer $accessToken") }.mapear { it.aPerfil() }

    private suspend fun <T : Any> llamar(peticion: suspend () -> Response<T>): ResultadoApi<T> = try {
        val respuesta = peticion()
        val cuerpo = respuesta.body()
        when {
            respuesta.isSuccessful && cuerpo != null -> ResultadoApi.Exito(cuerpo)
            respuesta.isSuccessful -> ResultadoApi.Fallo(respuesta.code(), null, null)
            else -> fallo(respuesta)
        }
    } catch (error: IOException) {
        ResultadoApi.SinConexion
    }

    private fun fallo(respuesta: Response<*>): ResultadoApi.Fallo {
        val (codigo, mensaje) = leerError(respuesta.errorBody()?.string())
        return ResultadoApi.Fallo(respuesta.code(), codigo, mensaje)
    }

    companion object {
        /**
         * El backend responde `{"detail": {"codigo": "...", "mensaje": "..."}}` o
         * `{"detail": "mensaje"}`. Cualquier otra forma se ignora.
         */
        fun leerError(cuerpo: String?): Pair<String?, String?> {
            if (cuerpo.isNullOrBlank()) return null to null
            return try {
                val detalle = JsonParser.parseString(cuerpo).asJsonObject.get("detail")
                when {
                    detalle == null || detalle.isJsonNull -> null to null
                    detalle.isJsonPrimitive -> null to detalle.asString
                    detalle.isJsonObject -> {
                        val objeto = detalle.asJsonObject
                        val codigo = objeto.get("codigo")?.takeIf { it.isJsonPrimitive }?.asString
                        val mensaje = objeto.get("mensaje")?.takeIf { it.isJsonPrimitive }?.asString
                        codigo to mensaje
                    }
                    else -> null to null
                }
            } catch (error: RuntimeException) {
                null to null
            }
        }
    }
}
