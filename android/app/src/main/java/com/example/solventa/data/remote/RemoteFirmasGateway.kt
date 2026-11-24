package com.example.solventa.data.remote

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.firmas.FirmasGateway
import com.example.solventa.domain.firmas.ProcesoFirma
import com.google.gson.JsonParseException
import com.google.gson.stream.MalformedJsonException
import java.io.IOException

class RemoteFirmasGateway(private val api: FirmasApi) : FirmasGateway {
    override suspend fun presentar(accessToken: String, cotizacionId: String) = ejecutar {
        api.presentar("Bearer $accessToken", cotizacionId).aResultado()
    }

    override suspend fun solicitarOtp(accessToken: String, cotizacionId: String) = ejecutar {
        api.solicitarOtp("Bearer $accessToken", cotizacionId).aResultado()
    }

    override suspend fun firmar(
        accessToken: String,
        cotizacionId: String,
        codigo: String,
        huellaDocumento: String
    ) = ejecutar {
        api.firmar(
            autorizacion = "Bearer $accessToken",
            cotizacionId = cotizacionId,
            solicitud = SolicitudFirmaDto(codigo, huellaDocumento)
        ).aResultado()
    }

    private fun retrofit2.Response<FirmaDto>.aResultado(): ResultadoApi<ProcesoFirma> {
        val proceso = body()?.aDominio()
        return when {
            isSuccessful && proceso != null -> ResultadoApi.Exito(proceso)
            isSuccessful -> ResultadoApi.Fallo(code(), null, null)
            else -> {
                val (codigo, mensaje) = RemoteAuthGateway.leerError(errorBody()?.string())
                ResultadoApi.Fallo(code(), codigo, mensaje)
            }
        }
    }

    private suspend fun ejecutar(operacion: suspend () -> ResultadoApi<ProcesoFirma>): ResultadoApi<ProcesoFirma> =
        try {
            operacion()
        } catch (_: MalformedJsonException) {
            ResultadoApi.Fallo(0, null, null)
        } catch (_: JsonParseException) {
            ResultadoApi.Fallo(0, null, null)
        } catch (_: IOException) {
            ResultadoApi.SinConexion
        }
}
