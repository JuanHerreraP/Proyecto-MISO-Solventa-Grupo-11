package com.example.solventa.data.remote

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

/**
 * Endpoints de siniestros (HU20). El backend filtra por la identidad del token: la app nunca
 * envía el identificador del cliente. La lista incluye los siniestros automáticos creados por
 * la telemetría externa y los manuales.
 */
interface SiniestrosApi {
    @GET("api/v1/siniestros")
    suspend fun listar(
        @Header("Authorization") autorizacion: String
    ): Response<List<SiniestroDto>>

    @POST("api/v1/siniestros")
    suspend fun registrar(
        @Header("Authorization") autorizacion: String,
        @Body solicitud: SolicitudSiniestroDto
    ): Response<SiniestroDto>
}
