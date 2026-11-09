package com.example.solventa.data.remote

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path

/**
 * Endpoints del asesor de ventas (HU20). El `asesor_id` lo toma el backend de la identidad
 * del token; la app nunca lo envía. Todos requieren el rol ASESOR_VENTAS.
 */
interface AsesorApi {
    @GET("api/v1/asesor/clientes")
    suspend fun listarClientes(
        @Header("Authorization") autorizacion: String
    ): Response<List<ClienteDeAsesorDto>>

    @POST("api/v1/asesor/clientes")
    suspend fun asociarCliente(
        @Header("Authorization") autorizacion: String,
        @Body solicitud: SolicitudAsociarClienteDto
    ): Response<ClienteDeAsesorDto>

    @GET("api/v1/asesor/clientes/{clienteId}/polizas")
    suspend fun polizasDeCliente(
        @Header("Authorization") autorizacion: String,
        @Path("clienteId") clienteId: String
    ): Response<BilleteraDto>

    /**
     * Alta de un asesor de ventas. La realiza un manager (SERVICIO_INTERNO) contra el endpoint
     * administrativo de usuarios; el rol se fija en el cuerpo.
     */
    @POST("api/v1/auth/users")
    suspend fun crearAsesor(
        @Header("Authorization") autorizacion: String,
        @Body solicitud: SolicitudCrearAsesorDto
    ): Response<RespuestaCrearAsesorDto>

    /**
     * Alta de un analista de cumplimiento. La realiza un manager (SERVICIO_INTERNO) contra el
     * mismo endpoint administrativo de usuarios; el rol se fija en el cuerpo.
     */
    @POST("api/v1/auth/users")
    suspend fun crearAnalista(
        @Header("Authorization") autorizacion: String,
        @Body solicitud: SolicitudCrearAnalistaDto
    ): Response<RespuestaCrearAsesorDto>
}
