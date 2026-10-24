package com.example.solventa.data.remote

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path

/** Recaudo inicial de la prima (HU13). El POST exige el encabezado Idempotency-Key. */
interface PagosApi {
    @POST("api/v1/pagos")
    suspend fun pagar(
        @Header("Authorization") autorizacion: String,
        @Header("Idempotency-Key") idempotencyKey: String,
        @Body solicitud: SolicitudPagoDto
    ): Response<PagoDto>

    @GET("api/v1/pagos/{pagoId}")
    suspend fun consultar(
        @Header("Authorization") autorizacion: String,
        @Path("pagoId") pagoId: String
    ): Response<PagoDto>

    @GET("api/v1/pagos")
    suspend fun listar(
        @Header("Authorization") autorizacion: String
    ): Response<List<PagoDto>>
}
