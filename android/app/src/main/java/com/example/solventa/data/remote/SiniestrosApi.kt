package com.example.solventa.data.remote

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

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

    /** Con `Idempotency-Key` (HU04), reenviar un borrador devuelve el siniestro ya creado. */
    @POST("api/v1/siniestros")
    suspend fun registrar(
        @Header("Authorization") autorizacion: String,
        @Body solicitud: SolicitudSiniestroDto,
        @Header("Idempotency-Key") claveIdempotencia: String?
    ): Response<SiniestroDto>

    /** Registro asistido por un asesor (HU20): el cuerpo incluye el cliente. */
    @POST("api/v1/siniestros/asistido")
    suspend fun registrarAsistido(
        @Header("Authorization") autorizacion: String,
        @Body solicitud: SolicitudSiniestroAsistidoDto
    ): Response<SiniestroDto>

    /** Un asesor lista los siniestros de un cliente asociado. */
    @GET("api/v1/siniestros")
    suspend fun listarDeCliente(
        @Header("Authorization") autorizacion: String,
        @Query("cliente_id") clienteId: String
    ): Response<List<SiniestroDto>>

    /**
     * Adjunta una foto o video (HU04). `X-Contenido-SHA256` permite al backend verificar que el
     * archivo llegó íntegro. Las partes nulas no se envían.
     */
    @Multipart
    @POST("api/v1/siniestros/{siniestroId}/evidencias")
    suspend fun subirEvidencia(
        @Header("Authorization") autorizacion: String,
        @Header("X-Contenido-SHA256") huella: String,
        @Path("siniestroId") siniestroId: String,
        @Part archivo: MultipartBody.Part,
        @Part("capturada_en") capturadaEn: RequestBody?,
        @Part("latitud") latitud: RequestBody?,
        @Part("longitud") longitud: RequestBody?,
        @Part("precision_metros") precisionMetros: RequestBody?
    ): Response<EvidenciaDto>
}
