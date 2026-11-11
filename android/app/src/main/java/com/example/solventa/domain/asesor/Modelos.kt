package com.example.solventa.domain.asesor

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.Billetera

/**
 * Un cliente atendido por el asesor de ventas (HU20). Son los datos mínimos que el asesor
 * necesita para elegir a quién registrarle un siniestro.
 */
data class ClienteDeAsesor(
    val clienteId: String,
    val nombre: String,
    val apellido: String,
    val email: String
) {
    val nombreCompleto: String get() = "$nombre $apellido"
}

/**
 * Datos que un manager ingresa para crear un asesor de ventas (HU20). El rol y el
 * consentimiento de identidad los fija la capa de datos.
 */
data class DatosNuevoAsesor(
    val nombre: String,
    val apellido: String,
    val email: String,
    val password: String,
    val tipoDocumento: String,
    val numeroDocumento: String,
    val fechaNacimiento: String
)

/**
 * Datos que un manager ingresa para crear un analista de cumplimiento (HU25). Mismos campos
 * que un asesor; solo cambia el rol que fija la capa de datos (ANALISTA_CUMPLIMIENTO).
 */
data class DatosNuevoAnalista(
    val nombre: String,
    val apellido: String,
    val email: String,
    val password: String,
    val tipoDocumento: String,
    val numeroDocumento: String,
    val fechaNacimiento: String
)

/**
 * Puerto hacia el backend del asesor (endpoints `/api/v1/asesor/...`). El `asesor_id` lo toma
 * el backend de la identidad del token; la app nunca lo envía.
 */
interface AsesorGateway {
    /** Clientes que atiende el asesor autenticado. */
    suspend fun listarClientes(accessToken: String): ResultadoApi<List<ClienteDeAsesor>>

    /** Asocia a un cliente identificándolo por su correo. */
    suspend fun asociarCliente(accessToken: String, email: String): ResultadoApi<ClienteDeAsesor>

    /** Pólizas de un cliente asociado, para elegir la afectada en un siniestro. */
    suspend fun polizasDeCliente(
        accessToken: String,
        clienteId: String
    ): ResultadoApi<Billetera>

    /** Alta de un asesor de ventas. Solo un manager (SERVICIO_INTERNO) puede hacerla. */
    suspend fun crearAsesor(
        accessToken: String,
        datos: DatosNuevoAsesor
    ): ResultadoApi<ClienteDeAsesor>

    /** Alta de un analista de cumplimiento. Solo un manager (SERVICIO_INTERNO) puede hacerla. */
    suspend fun crearAnalista(
        accessToken: String,
        datos: DatosNuevoAnalista
    ): ResultadoApi<ClienteDeAsesor>
}
