package com.example.solventa.data.remote

import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path

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

    @POST("api/v1/billetera/polizas/{polizaId}/enlaces")
    suspend fun compartir(
        @Header("Authorization") autorizacion: String,
        @Path("polizaId") polizaId: String
    ): Response<EnlaceCompartidoDto>
}
