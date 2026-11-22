package com.example.solventa.data.remote

import com.example.solventa.domain.asistencias.Asistencia
import com.example.solventa.domain.asistencias.AsistenciasGateway
import com.example.solventa.domain.asistencias.NuevaAsistencia
import com.example.solventa.domain.asistencias.PrestadoresCercanos
import com.example.solventa.domain.asistencias.ServiciosPoliza
import com.example.solventa.domain.asistencias.TipoServicio
import com.example.solventa.domain.auth.ResultadoApi
import com.google.gson.JsonParseException
import com.google.gson.stream.MalformedJsonException
import java.io.IOException
import retrofit2.Response

/** Adaptador Retrofit del puerto de asistencias (HU06). */
class RemoteAsistenciasGateway(private val api: AsistenciasApi) : AsistenciasGateway {

    override suspend fun servicios(
        accessToken: String,
        polizaId: String
    ): ResultadoApi<ServiciosPoliza> =
        llamar({ api.servicios(bearer(accessToken), polizaId) }) { it.aDominio() }

    override suspend fun prestadoresCercanos(
        accessToken: String,
        polizaId: String,
        servicio: TipoServicio,
        latitud: Double,
        longitud: Double,
        radioKm: Double
    ): ResultadoApi<PrestadoresCercanos> =
        llamar({
            api.prestadoresCercanos(
                bearer(accessToken), polizaId, servicio.name, latitud, longitud, radioKm
            )
        }) { it.aDominio() }

    override suspend fun solicitar(
        accessToken: String,
        solicitud: NuevaAsistencia
    ): ResultadoApi<Asistencia> =
        llamar({ api.solicitar(bearer(accessToken), solicitud.aDto()) }) { it.aDominio() }

    override suspend fun listar(accessToken: String): ResultadoApi<List<Asistencia>> =
        llamar({ api.listar(bearer(accessToken)) }) { it.aAsistencias() }

    override suspend fun cancelar(
        accessToken: String,
        asistenciaId: String
    ): ResultadoApi<Asistencia> =
        llamar({ api.cancelar(bearer(accessToken), asistenciaId) }) { it.aDominio() }

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
            if (valor != null) {
                ResultadoApi.Exito(valor)
            } else {
                ResultadoApi.Fallo(respuesta.code(), null, null)
            }
        } else {
            val (codigo, mensaje) = RemoteAuthGateway.leerError(respuesta.errorBody()?.string())
            ResultadoApi.Fallo(respuesta.code(), codigo, mensaje)
        }
    } catch (error: MalformedJsonException) {
        ResultadoApi.Fallo(CUERPO_INVALIDO, null, null)
    } catch (error: IOException) {
        ResultadoApi.SinConexion
    } catch (error: JsonParseException) {
        ResultadoApi.Fallo(CUERPO_INVALIDO, null, null)
    }

    private companion object {
        const val CUERPO_INVALIDO = 0
    }
}
