package com.example.solventa.data.remote

import com.example.solventa.domain.auth.Perfil
import com.example.solventa.domain.auth.Tokens
import com.google.gson.annotations.SerializedName

data class SolicitudLoginDto(
    @SerializedName("email") val email: String,
    @SerializedName("password") val password: String
)

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
