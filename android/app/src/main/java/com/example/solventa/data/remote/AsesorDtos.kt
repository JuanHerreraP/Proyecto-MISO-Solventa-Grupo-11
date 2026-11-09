package com.example.solventa.data.remote

import com.example.solventa.domain.asesor.ClienteDeAsesor
import com.google.gson.annotations.SerializedName

/**
 * Gson no pasa por el constructor de Kotlin: un campo ausente llega como null aunque el tipo
 * no lo permita. Por eso los DTO son anulables y el mapeo descarta lo incompleto.
 */
data class ClienteDeAsesorDto(
    @SerializedName("cliente_id") val clienteId: String?,
    @SerializedName("nombre") val nombre: String?,
    @SerializedName("apellido") val apellido: String?,
    @SerializedName("email") val email: String?
) {
    fun aCliente(): ClienteDeAsesor? {
        return ClienteDeAsesor(
            clienteId = clienteId ?: return null,
            nombre = nombre.orEmpty(),
            apellido = apellido.orEmpty(),
            email = email.orEmpty()
        )
    }
}

/** El asesor asocia a un cliente identificándolo por su correo. */
data class SolicitudAsociarClienteDto(
    @SerializedName("email") val email: String
)

/**
 * Cuerpo del alta de un asesor (POST /api/v1/auth/users). El rol se fija a ASESOR_VENTAS y se
 * acepta la validación de identidad, como en el portal web.
 */
data class SolicitudCrearAsesorDto(
    @SerializedName("nombre") val nombre: String,
    @SerializedName("apellido") val apellido: String,
    @SerializedName("email") val email: String,
    @SerializedName("password") val password: String,
    @SerializedName("tipo_documento") val tipoDocumento: String,
    @SerializedName("numero_documento") val numeroDocumento: String,
    @SerializedName("fecha_nacimiento") val fechaNacimiento: String,
    @SerializedName("acepta_validacion_identidad") val aceptaValidacionIdentidad: Boolean = true,
    @SerializedName("rol") val rol: String = "ASESOR_VENTAS"
)

data class RespuestaCrearAsesorDto(
    @SerializedName("id") val id: String?,
    @SerializedName("nombre") val nombre: String?,
    @SerializedName("apellido") val apellido: String?,
    @SerializedName("email") val email: String?,
    @SerializedName("rol") val rol: String?
) {
    fun aCliente(): ClienteDeAsesor? {
        return ClienteDeAsesor(
            clienteId = id ?: return null,
            nombre = nombre.orEmpty(),
            apellido = apellido.orEmpty(),
            email = email.orEmpty()
        )
    }
}

/**
 * Cuerpo del alta de un analista de cumplimiento (POST /api/v1/auth/users). Igual que el del
 * asesor pero con el rol ANALISTA_CUMPLIMIENTO (HU25), como en el portal web.
 */
data class SolicitudCrearAnalistaDto(
    @SerializedName("nombre") val nombre: String,
    @SerializedName("apellido") val apellido: String,
    @SerializedName("email") val email: String,
    @SerializedName("password") val password: String,
    @SerializedName("tipo_documento") val tipoDocumento: String,
    @SerializedName("numero_documento") val numeroDocumento: String,
    @SerializedName("fecha_nacimiento") val fechaNacimiento: String,
    @SerializedName("acepta_validacion_identidad") val aceptaValidacionIdentidad: Boolean = true,
    @SerializedName("rol") val rol: String = "ANALISTA_CUMPLIMIENTO"
)

/** Mapea la lista JSON a dominio, conservando el orden del backend (alfabético por nombre). */
fun List<ClienteDeAsesorDto>.aClientes(): List<ClienteDeAsesor> = mapNotNull { it.aCliente() }
