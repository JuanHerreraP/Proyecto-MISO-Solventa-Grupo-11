package com.example.solventa.data.remote

import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Streaming

/**
 * Endpoints de la billetera (HU07). El backend filtra por la identidad del token: la app
 * nunca envía el identificador del cliente.
 */
interface PolizasApi {
    @GET("api/v1/billetera/polizas")
    suspend fun billetera(@Header("Authorization") autorizacion: String): Response<BilleteraDto>

    @GET("api/v1/billetera/polizas/{polizaId}/certificado")
    suspend fun certificado(
        @Header("Authorization") autorizacion: String,
        @Path("polizaId") polizaId: String
    ): Response<CertificadoDto>

    @GET("api/v1/polizas/{polizaId}/historial")
    suspend fun historialPoliza(
        @Header("Authorization") autorizacion: String,
        @Path("polizaId") polizaId: String
    ): Response<HistorialPolizaDto>

    @Streaming
    @GET("api/v1/polizas/{polizaId}/documento")
    suspend fun documento(
        @Header("Authorization") autorizacion: String,
        @Path("polizaId") polizaId: String
    ): Response<ResponseBody>

    @POST("api/v1/billetera/polizas/{polizaId}/enlaces")
    suspend fun compartir(
        @Header("Authorization") autorizacion: String,
        @Path("polizaId") polizaId: String
    ): Response<EnlaceCompartidoDto>
}
