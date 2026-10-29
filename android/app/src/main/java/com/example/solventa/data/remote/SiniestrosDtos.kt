package com.example.solventa.data.remote

import com.example.solventa.domain.siniestros.EstadoSiniestro
import com.example.solventa.domain.siniestros.OrigenSiniestro
import com.example.solventa.domain.siniestros.Siniestro
import com.example.solventa.domain.siniestros.Siniestros
import com.example.solventa.domain.siniestros.SolicitudSiniestro
import com.google.gson.annotations.SerializedName
import java.math.BigDecimal

/**
 * Gson no pasa por el constructor de Kotlin: un campo ausente llega como null aunque el tipo
 * no lo permita. Por eso los DTO son anulables y el mapeo descarta lo incompleto o desconocido.
 */
data class SiniestroDto(
    @SerializedName("siniestro_id") val siniestroId: String?,
    @SerializedName("poliza_id") val polizaId: String?,
    @SerializedName("origen") val origen: String?,
    @SerializedName("estado") val estado: String?,
    @SerializedName("evento_id") val eventoId: String?,
    @SerializedName("fecha_evento") val fechaEvento: String?,
    @SerializedName("hora_evento") val horaEvento: String?,
    @SerializedName("lugar") val lugar: String?,
    @SerializedName("descripcion") val descripcion: String?,
    @SerializedName("estimacion_danos") val estimacionDanos: String?,
    @SerializedName("moneda") val moneda: String?,
    @SerializedName("registrado_en") val registradoEn: String?
) {
    fun aSiniestro(): Siniestro? {
        val origenSiniestro = origen.aOrigen() ?: return null
        val estadoSiniestro = estado.aEstado() ?: return null
        return Siniestro(
            siniestroId = siniestroId ?: return null,
            polizaId = polizaId ?: return null,
            origen = origenSiniestro,
            estado = estadoSiniestro,
            eventoId = eventoId,
            fechaEvento = fechaEvento ?: return null,
            horaEvento = horaEvento.orEmpty(),
            lugar = lugar.orEmpty(),
            descripcion = descripcion.orEmpty(),
            estimacionDanos = estimacionDanos.orEmpty(),
            moneda = moneda ?: "COP",
            registradoEn = registradoEn ?: return null
        )
    }
}

/** Mapea la lista JSON a dominio, conservando el orden del backend (más reciente primero). */
fun List<SiniestroDto>.aSiniestros(): Siniestros =
    Siniestros(siniestros = mapNotNull { it.aSiniestro() })

/**
 * Cuerpo del registro manual (HU20). `estimacion_danos` viaja como número; la validación de la
 * UI garantiza que el texto es un decimal >= 0 antes de llegar aquí.
 */
data class SolicitudSiniestroDto(
    @SerializedName("poliza_id") val polizaId: String,
    @SerializedName("fecha_evento") val fechaEvento: String,
    @SerializedName("hora_evento") val horaEvento: String,
    @SerializedName("lugar") val lugar: String,
    @SerializedName("descripcion") val descripcion: String,
    @SerializedName("estimacion_danos") val estimacionDanos: BigDecimal
)

fun SolicitudSiniestro.aDto(): SolicitudSiniestroDto = SolicitudSiniestroDto(
    polizaId = polizaId,
    fechaEvento = fechaEvento,
    horaEvento = horaEvento,
    lugar = lugar,
    descripcion = descripcion,
    estimacionDanos = estimacionDanos.toBigDecimalOrNull() ?: BigDecimal.ZERO
)

private fun String?.aOrigen(): OrigenSiniestro? =
    this?.let { valor -> OrigenSiniestro.entries.firstOrNull { it.name == valor } }

private fun String?.aEstado(): EstadoSiniestro? =
    this?.let { valor -> EstadoSiniestro.entries.firstOrNull { it.name == valor } }
