package com.example.solventa.data.remote

import com.example.solventa.domain.auth.Perfil
import com.example.solventa.domain.auth.DatosRegistro
import com.example.solventa.domain.auth.RegistroCreado
import com.example.solventa.domain.auth.Tokens
import com.google.gson.annotations.SerializedName

data class SolicitudLoginDto(
    @SerializedName("email") val email: String,
    @SerializedName("password") val password: String
)

data class SolicitudRegistroDto(
    @SerializedName("nombre") val nombre: String,
    @SerializedName("apellido") val apellido: String,
    @SerializedName("email") val email: String,
    @SerializedName("password") val password: String,
    @SerializedName("tipo_documento") val tipoDocumento: String,
    @SerializedName("numero_documento") val numeroDocumento: String,
    @SerializedName("fecha_nacimiento") val fechaNacimiento: String,
    @SerializedName("celular") val celular: String,
    @SerializedName("acepta_validacion_identidad") val aceptaValidacionIdentidad: Boolean,
    @SerializedName("selfie_base64") val selfieBase64: String
) {
    companion object {
        fun desde(datos: DatosRegistro) = SolicitudRegistroDto(
            nombre = datos.nombre,
            apellido = datos.apellido,
            email = datos.email,
            password = datos.password,
            tipoDocumento = datos.tipoDocumento,
            numeroDocumento = datos.numeroDocumento,
            fechaNacimiento = datos.fechaNacimiento,
            celular = datos.celular,
            aceptaValidacionIdentidad = true,
            selfieBase64 = datos.selfieBase64
        )
    }
}

data class RespuestaRegistroDto(
    @SerializedName("email") val email: String,
    @SerializedName("kyc_validado") val kycValidado: Boolean
) {
    fun aRegistroCreado() = RegistroCreado(email = email, kycValidado = kycValidado)
}

data class SolicitudRefreshDto(
    @SerializedName("refresh_token") val refreshToken: String
)

data class RespuestaTokensDto(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String,
    @SerializedName("token_type") val tokenType: String,
    @SerializedName("expires_in") val expiresIn: Long,
    @SerializedName("refresh_expires_in") val refreshExpiresIn: Long
) {
    fun aTokens() = Tokens(
        accessToken = accessToken,
        refreshToken = refreshToken,
        expiraEnSegundos = expiresIn
    )
}

data class PerfilDto(
    @SerializedName("id") val id: String,
    @SerializedName("nombre") val nombre: String,
    @SerializedName("apellido") val apellido: String,
    @SerializedName("email") val email: String,
    @SerializedName("rol") val rol: String
) {
    fun aPerfil() = Perfil(id = id, nombre = nombre, apellido = apellido, email = email, rol = rol)
}
