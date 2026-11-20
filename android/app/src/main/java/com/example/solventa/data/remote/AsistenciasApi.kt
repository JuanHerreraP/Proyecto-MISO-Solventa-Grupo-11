package com.example.solventa.data.remote

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Endpoints de asistencia en sitio (HU06). El backend filtra por la identidad del token: la app
 * nunca envía el identificador del cliente.
 */
interface AsistenciasApi {
    @GET("api/v1/asistencias/servicios")
    suspend fun servicios(
        @Header("Authorization") autorizacion: String,
        @Query("poliza_id") polizaId: String
    ): Response<ServiciosPolizaDto>

    @GET("api/v1/prestadores/cercanos")
    suspend fun prestadoresCercanos(
        @Header("Authorization") autorizacion: String,
        @Query("poliza_id") polizaId: String,
        @Query("servicio") servicio: String,
        @Query("latitud") latitud: Double,
        @Query("longitud") longitud: Double,
        @Query("radio_km") radioKm: Double
    ): Response<PrestadoresCercanosDto>

    @POST("api/v1/asistencias")
    suspend fun solicitar(
        @Header("Authorization") autorizacion: String,
        @Body solicitud: NuevaAsistenciaDto
    ): Response<AsistenciaDto>

    @GET("api/v1/asistencias")
    suspend fun listar(
        @Header("Authorization") autorizacion: String
    ): Response<List<AsistenciaDto>>

    @POST("api/v1/asistencias/{asistenciaId}/cancelacion")
    suspend fun cancelar(
        @Header("Authorization") autorizacion: String,
        @Path("asistenciaId") asistenciaId: String
    ): Response<AsistenciaDto>
}
