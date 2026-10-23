package com.example.solventa.data.remote

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface CotizacionesApi {
    @GET("api/v1/cotizaciones")
    suspend fun listar(
        @Header("Authorization") autorizacion: String,
        @Query("cliente_id") clienteId: String
    ): Response<List<CotizacionDto>>

    @POST("api/v1/cotizaciones")
    suspend fun cotizar(
        @Header("Authorization") autorizacion: String,
        @Body solicitud: SolicitudCotizacionDto
    ): Response<CotizacionDto>
}

