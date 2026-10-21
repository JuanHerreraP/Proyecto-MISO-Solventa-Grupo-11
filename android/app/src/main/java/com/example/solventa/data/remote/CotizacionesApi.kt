package com.example.solventa.data.remote

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.POST

interface CotizacionesApi {
    @POST("api/v1/cotizaciones")
    suspend fun cotizar(
        @Header("Authorization") autorizacion: String,
        @Body solicitud: SolicitudCotizacionDto
    ): Response<CotizacionDto>
}

