package com.example.solventa.data.remote

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.cotizaciones.CotizacionesGateway
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.example.solventa.domain.cotizaciones.ResultadoCotizacion
import com.google.gson.JsonParseException
import com.google.gson.stream.MalformedJsonException
import java.io.IOException

class RemoteCotizacionesGateway(private val api: CotizacionesApi) : CotizacionesGateway {
    override suspend fun cotizar(
        accessToken: String,
        clienteId: String,
        ramo: RamoCotizacion,
        datosRiesgo: Map<String, Any>
    ): ResultadoApi<ResultadoCotizacion> = try {
        val respuesta = api.cotizar(
            autorizacion = "Bearer $accessToken",
            solicitud = SolicitudCotizacionDto(clienteId, ramo.codigoApi, datosRiesgo)
        )
        val resultado = respuesta.body()?.aResultado()
        when {
            respuesta.isSuccessful && resultado != null -> ResultadoApi.Exito(resultado)
            respuesta.isSuccessful -> ResultadoApi.Fallo(respuesta.code(), null, null)
            else -> {
                val (codigo, mensaje) = RemoteAuthGateway.leerError(respuesta.errorBody()?.string())
                ResultadoApi.Fallo(respuesta.code(), codigo, mensaje)
            }
        }
    } catch (error: MalformedJsonException) {
        ResultadoApi.Fallo(0, null, null)
    } catch (error: JsonParseException) {
        ResultadoApi.Fallo(0, null, null)
    } catch (error: IOException) {
        ResultadoApi.SinConexion
    }
}

