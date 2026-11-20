package com.example.solventa.data.remote

import com.example.solventa.domain.asistencias.Asistencia
import com.example.solventa.domain.asistencias.EstadoAsistencia
import com.example.solventa.domain.asistencias.NuevaAsistencia
import com.example.solventa.domain.asistencias.PrestadorCercano
import com.example.solventa.domain.asistencias.PrestadorResumen
import com.example.solventa.domain.asistencias.PrestadoresCercanos
import com.example.solventa.domain.asistencias.ServicioAsistencia
import com.example.solventa.domain.asistencias.ServiciosPoliza
import com.example.solventa.domain.asistencias.TipoServicio
import com.google.gson.annotations.SerializedName

/**
 * Gson no pasa por el constructor de Kotlin: un campo ausente llega como null aunque el tipo
 * no lo permita. Por eso los DTO son anulables y el mapeo descarta lo incompleto o desconocido.
 */
data class ServicioDisponibleDto(
    @SerializedName("codigo") val codigo: String?,
    @SerializedName("nombre") val nombre: String?
) {
    fun aDominio(): ServicioAsistencia? {
        val tipo = TipoServicio.desdeCodigo(codigo) ?: return null
        return ServicioAsistencia(codigo = tipo, nombre = nombre ?: tipo.etiqueta)
    }
}

data class ServiciosPolizaDto(
    @SerializedName("poliza_id") val polizaId: String?,
    @SerializedName("ramo") val ramo: String?,
    @SerializedName("servicios") val servicios: List<ServicioDisponibleDto>?
) {
    fun aDominio(): ServiciosPoliza? {
        val id = polizaId ?: return null
        return ServiciosPoliza(
            polizaId = id,
            ramo = ramo.orEmpty(),
            servicios = servicios.orEmpty().mapNotNull { it.aDominio() }
        )
    }
}

data class PrestadorCercanoDto(
    @SerializedName("prestador_id") val prestadorId: String?,
    @SerializedName("nombre") val nombre: String?,
    @SerializedName("tipo_servicio") val tipoServicio: String?,
    @SerializedName("direccion") val direccion: String?,
    @SerializedName("telefono") val telefono: String?,
    @SerializedName("latitud") val latitud: Double?,
    @SerializedName("longitud") val longitud: Double?,
    @SerializedName("distancia_km") val distanciaKm: Double?
) {
    fun aDominio(): PrestadorCercano? {
        val tipo = TipoServicio.desdeCodigo(tipoServicio) ?: return null
        return PrestadorCercano(
            prestadorId = prestadorId ?: return null,
            nombre = nombre ?: return null,
            tipoServicio = tipo,
            direccion = direccion.orEmpty(),
            telefono = telefono,
            latitud = latitud ?: return null,
            longitud = longitud ?: return null,
            distanciaKm = distanciaKm ?: 0.0
        )
    }
}

data class PrestadoresCercanosDto(
    @SerializedName("poliza_id") val polizaId: String?,
    @SerializedName("servicio") val servicio: String?,
    @SerializedName("ubicacion") val ubicacion: UbicacionDto?,
    @SerializedName("prestadores") val prestadores: List<PrestadorCercanoDto>?
) {
    fun aDominio(): PrestadoresCercanos? {
        val tipo = TipoServicio.desdeCodigo(servicio) ?: return null
        return PrestadoresCercanos(
            polizaId = polizaId ?: return null,
            servicio = tipo,
            latitud = ubicacion?.latitud ?: 0.0,
            longitud = ubicacion?.longitud ?: 0.0,
            prestadores = prestadores.orEmpty().mapNotNull { it.aDominio() }
        )
    }
}

data class UbicacionDto(
    @SerializedName("latitud") val latitud: Double?,
    @SerializedName("longitud") val longitud: Double?
)

data class PrestadorResumenDto(
    @SerializedName("prestador_id") val prestadorId: String?,
    @SerializedName("nombre") val nombre: String?,
    @SerializedName("telefono") val telefono: String?
) {
    fun aDominio(): PrestadorResumen? {
        val id = prestadorId ?: return null
        return PrestadorResumen(
            prestadorId = id,
            nombre = nombre ?: return null,
            telefono = telefono
        )
    }
}

/** Cuerpo del POST de creación. El cliente nunca envía su identificador ni el estado. */
data class NuevaAsistenciaDto(
    @SerializedName("poliza_id") val polizaId: String,
    @SerializedName("prestador_id") val prestadorId: String,
    @SerializedName("servicio") val servicio: String,
    @SerializedName("latitud") val latitud: Double,
    @SerializedName("longitud") val longitud: Double,
    @SerializedName("observaciones") val observaciones: String?
)

fun NuevaAsistencia.aDto(): NuevaAsistenciaDto = NuevaAsistenciaDto(
    polizaId = polizaId,
    prestadorId = prestadorId,
    servicio = servicio.name,
    latitud = latitud,
    longitud = longitud,
    observaciones = observaciones
)

data class AsistenciaDto(
    @SerializedName("asistencia_id") val asistenciaId: String?,
    @SerializedName("poliza_id") val polizaId: String?,
    @SerializedName("prestador") val prestador: PrestadorResumenDto?,
    @SerializedName("servicio") val servicio: String?,
    @SerializedName("estado") val estado: String?,
    @SerializedName("ubicacion") val ubicacion: UbicacionDto?,
    @SerializedName("observaciones") val observaciones: String?,
    @SerializedName("creada_en") val creadaEn: String?,
    @SerializedName("cancelada_en") val canceladaEn: String?,
    @SerializedName("aceptada_en") val aceptadaEn: String? = null,
    @SerializedName("tiempo_estimado_llegada_minutos") val tiempoEstimadoLlegadaMinutos: Int? = null
) {
    fun aDominio(): Asistencia? {
        val tipo = TipoServicio.desdeCodigo(servicio) ?: return null
        val estadoAsistencia = EstadoAsistencia.desdeCodigo(estado) ?: return null
        return Asistencia(
            asistenciaId = asistenciaId ?: return null,
            polizaId = polizaId ?: return null,
            prestador = prestador?.aDominio() ?: return null,
            servicio = tipo,
            estado = estadoAsistencia,
            latitud = ubicacion?.latitud ?: 0.0,
            longitud = ubicacion?.longitud ?: 0.0,
            observaciones = observaciones,
            creadaEn = creadaEn ?: return null,
            canceladaEn = canceladaEn,
            aceptadaEn = aceptadaEn,
            tiempoEstimadoLlegadaMinutos = tiempoEstimadoLlegadaMinutos
        )
    }
}

fun List<AsistenciaDto>.aAsistencias(): List<Asistencia> = mapNotNull { it.aDominio() }
