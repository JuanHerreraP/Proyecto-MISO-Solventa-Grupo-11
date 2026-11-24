package com.example.solventa.data.remote

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path

/** API existente de firma electrónica; no requiere cambios en backend. */
interface FirmasApi {
    @GET("api/v1/firmas/{cotizacionId}")
    suspend fun presentar(
        @Header("Authorization") autorizacion: String,
        @Path("cotizacionId") cotizacionId: String
    ): Response<FirmaDto>

    @POST("api/v1/firmas/{cotizacionId}/otp")
    suspend fun solicitarOtp(
        @Header("Authorization") autorizacion: String,
        @Path("cotizacionId") cotizacionId: String,
        @Body solicitud: SolicitudOtpDto = SolicitudOtpDto()
    ): Response<FirmaDto>

    @POST("api/v1/firmas/{cotizacionId}/firma")
    suspend fun firmar(
        @Header("Authorization") autorizacion: String,
        @Path("cotizacionId") cotizacionId: String,
        @Body solicitud: SolicitudFirmaDto
    ): Response<FirmaDto>
}
