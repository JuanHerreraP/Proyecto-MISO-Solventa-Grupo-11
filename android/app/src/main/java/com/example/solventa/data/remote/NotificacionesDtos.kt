package com.example.solventa.data.remote

import com.example.solventa.domain.notificaciones.Bandeja
import com.example.solventa.domain.notificaciones.Notificacion
import com.example.solventa.domain.notificaciones.TipoNotificacion
import com.google.gson.annotations.SerializedName

/**
 * Gson no pasa por el constructor de Kotlin: un campo ausente llega como null aunque el tipo no
 * lo permita. Por eso los DTO son anulables y el mapeo descarta lo incompleto o desconocido.
 */
data class NotificacionDto(
    @SerializedName("notificacion_id") val notificacionId: String?,
    @SerializedName("tipo") val tipo: String?,
    @SerializedName("titulo") val titulo: String?,
    @SerializedName("cuerpo") val cuerpo: String?,
    @SerializedName("datos") val datos: Map<String, String>?,
    @SerializedName("creada_en") val creadaEn: String?,
    @SerializedName("leida") val leida: Boolean?
) {
    fun aNotificacion(): Notificacion? {
        val id = notificacionId?.takeIf(String::isNotBlank) ?: return null
        // Un tipo que esta versión de la app no conoce se descarta en vez de mostrarse a medias.
        val tipoConocido = TipoNotificacion.desdeCodigo(tipo) ?: return null
        val tituloValido = titulo?.takeIf(String::isNotBlank) ?: return null
        val creada = creadaEn ?: return null
        return Notificacion(
            notificacionId = id,
            tipo = tipoConocido,
            titulo = tituloValido,
            cuerpo = cuerpo.orEmpty(),
            datos = datos.orEmpty(),
            creadaEn = creada,
            leida = leida == true
        )
    }
}

data class ListaNotificacionesDto(
    @SerializedName("notificaciones") val notificaciones: List<NotificacionDto>?,
    @SerializedName("no_leidas") val noLeidas: Int?
) {
    fun aBandeja(): Bandeja {
        val lista = notificaciones.orEmpty().mapNotNull(NotificacionDto::aNotificacion)
        return Bandeja(
            notificaciones = lista,
            noLeidas = noLeidas ?: lista.count { !it.leida }
        )
    }
}

data class ConteoNoLeidasDto(
    @SerializedName("no_leidas") val noLeidas: Int?
)

data class LecturaNotificacionDto(
    @SerializedName("notificacion_id") val notificacionId: String?,
    @SerializedName("leida") val leida: Boolean?,
    @SerializedName("no_leidas") val noLeidas: Int?
)

data class SolicitudDispositivoDto(
    @SerializedName("token") val token: String,
    @SerializedName("plataforma") val plataforma: String = "ANDROID"
)

data class BajaDispositivoDto(
    @SerializedName("token") val token: String
)

data class PreferenciaPushDto(
    @SerializedName("push_habilitado") val pushHabilitado: Boolean?
)
