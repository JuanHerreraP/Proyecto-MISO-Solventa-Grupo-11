package com.example.solventa.data.remote

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

/** Endpoints de identidad del backend (HU19 y HU02). */
interface AuthApi {
    @POST("api/v1/auth/login")
    suspend fun login(@Body solicitud: SolicitudLoginDto): Response<RespuestaTokensDto>

    @POST("api/v1/auth/refresh")
    suspend fun renovar(@Body solicitud: SolicitudRefreshDto): Response<RespuestaTokensDto>

    @POST("api/v1/auth/logout")
    suspend fun cerrarSesion(@Body solicitud: SolicitudRefreshDto): Response<Unit>

    @GET("api/v1/auth/me")
    suspend fun perfil(@Header("Authorization") autorizacion: String): Response<PerfilDto>
}
