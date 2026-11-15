package com.example.solventa.data.remote

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.pagos.ComprobantePago
import com.example.solventa.domain.pagos.Pago
import com.example.solventa.domain.pagos.PagosGateway
import com.example.solventa.domain.pagos.PrimaPendiente
import com.example.solventa.domain.pagos.SolicitudPago
import com.google.gson.JsonParseException
import com.google.gson.stream.MalformedJsonException
import java.io.IOException

class RemotePagosGateway(private val api: PagosApi) : PagosGateway {
    override suspend fun pagar(
        accessToken: String,
        idempotencyKey: String,
        solicitud: SolicitudPago
    ): ResultadoApi<Pago> = ejecutar {
        val respuesta = api.pagar(
            autorizacion = "Bearer $accessToken",
            idempotencyKey = idempotencyKey,
            solicitud = SolicitudPagoDto(
                cotizacionId = solicitud.cotizacionId,
                metodo = solicitud.metodo.codigoApi,
                tokenTarjeta = solicitud.tokenTarjeta,
                codigoBanco = solicitud.codigoBanco,
                urlRetorno = solicitud.urlRetorno
            )
        )
        val pago = respuesta.body()?.aDominio()
        when {
            respuesta.isSuccessful && pago != null -> ResultadoApi.Exito(pago)
            respuesta.isSuccessful -> ResultadoApi.Fallo(respuesta.code(), null, null)
            else -> respuesta.aFallo()
        }
    }

    override suspend fun consultar(
        accessToken: String,
        pagoId: String
    ): ResultadoApi<Pago> = ejecutar {
        val respuesta = api.consultar("Bearer $accessToken", pagoId)
        val pago = respuesta.body()?.aDominio()
        when {
            respuesta.isSuccessful && pago != null -> ResultadoApi.Exito(pago)
            respuesta.isSuccessful -> ResultadoApi.Fallo(respuesta.code(), null, null)
            else -> respuesta.aFallo()
        }
    }

    override suspend fun listar(accessToken: String): ResultadoApi<List<Pago>> = ejecutar {
        val respuesta = api.listar("Bearer $accessToken")
        val pagos = respuesta.body()?.mapNotNull(PagoDto::aDominio)
        when {
            respuesta.isSuccessful && pagos != null -> ResultadoApi.Exito(pagos)
            respuesta.isSuccessful -> ResultadoApi.Fallo(respuesta.code(), null, null)
            else -> respuesta.aFallo()
        }
    }

    override suspend fun pendientes(accessToken: String): ResultadoApi<List<PrimaPendiente>> =
        ejecutar {
            val respuesta = api.primasPendientes("Bearer $accessToken")
            val primas = respuesta.body()?.primas?.mapNotNull(PrimaPendienteDto::aDominio)
            when {
                respuesta.isSuccessful && primas != null -> ResultadoApi.Exito(primas)
                respuesta.isSuccessful -> ResultadoApi.Fallo(respuesta.code(), null, null)
                else -> respuesta.aFallo()
            }
        }

    override suspend fun comprobante(
        accessToken: String,
        pagoId: String
    ): ResultadoApi<ComprobantePago> = ejecutar {
        val respuesta = api.comprobante("Bearer $accessToken", pagoId)
        val comprobante = respuesta.body()?.aDominio()
        when {
            respuesta.isSuccessful && comprobante != null -> ResultadoApi.Exito(comprobante)
            respuesta.isSuccessful -> ResultadoApi.Fallo(respuesta.code(), null, null)
            else -> respuesta.aFallo()
        }
    }

    private suspend fun <T> ejecutar(
        operacion: suspend () -> ResultadoApi<T>
    ): ResultadoApi<T> = try {
        operacion()
    } catch (error: MalformedJsonException) {
        ResultadoApi.Fallo(0, null, null)
    } catch (error: JsonParseException) {
        ResultadoApi.Fallo(0, null, null)
    } catch (error: IOException) {
        ResultadoApi.SinConexion
    }

    private fun <T> retrofit2.Response<T>.aFallo(): ResultadoApi.Fallo {
        val (codigo, mensaje) = RemoteAuthGateway.leerError(errorBody()?.string())
        return ResultadoApi.Fallo(code(), codigo, mensaje)
    }
}
