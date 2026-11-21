package com.example.solventa.data.remote

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

/** Notificaciones del cliente (HU05): bandeja, dispositivos de push y preferencia. */
interface NotificacionesApi {
    @GET("api/v1/notificaciones")
    suspend fun listar(
        @Header("Authorization") autorizacion: String,
        @Query("limite") limite: Int = 50,
        @Query("desplazamiento") desplazamiento: Int = 0
    ): Response<ListaNotificacionesDto>

    @GET("api/v1/notificaciones/no-leidas")
    suspend fun contarNoLeidas(
        @Header("Authorization") autorizacion: String
    ): Response<ConteoNoLeidasDto>

    @POST("api/v1/notificaciones/{notificacionId}/leida")
    suspend fun marcarLeida(
        @Header("Authorization") autorizacion: String,
        @Path("notificacionId") notificacionId: String
    ): Response<LecturaNotificacionDto>

    @PUT("api/v1/notificaciones/dispositivos")
    suspend fun registrarDispositivo(
        @Header("Authorization") autorizacion: String,
        @Body solicitud: SolicitudDispositivoDto
    ): Response<Unit>

    @POST("api/v1/notificaciones/dispositivos/baja")
    suspend fun darDeBajaDispositivo(
        @Header("Authorization") autorizacion: String,
        @Body solicitud: BajaDispositivoDto
    ): Response<Unit>

    @GET("api/v1/notificaciones/preferencias")
    suspend fun obtenerPreferencia(
        @Header("Authorization") autorizacion: String
    ): Response<PreferenciaPushDto>

    @PUT("api/v1/notificaciones/preferencias")
    suspend fun cambiarPreferencia(
        @Header("Authorization") autorizacion: String,
        @Body solicitud: PreferenciaPushDto
    ): Response<PreferenciaPushDto>
}
