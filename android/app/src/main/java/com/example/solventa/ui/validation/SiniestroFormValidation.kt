package com.example.solventa.ui.validation

import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale
import com.example.solventa.R
import com.example.solventa.i18n.tr

/**
 * Validación del registro manual de siniestros (HU20), alineada con el backend:
 * - lugar: 1..200
 * - descripcion: 10..2000
 * - estimacion_danos: decimal >= 0
 * - fecha_evento: AAAA-MM-DD, no futura
 * - hora_evento: HH:MM (24h)
 * El backend hace la validación autoritativa (vigencia, titularidad); esto es ayuda temprana.
 */

private val formatoFechaIsoSiniestro = Regex("^\\d{4}-\\d{2}-\\d{2}$")
private val formatoHora = Regex("^([01]\\d|2[0-3]):[0-5]\\d$")
private val formatoDecimal = Regex("^\\d{1,15}([.,]\\d{1,2})?$")

fun errorPolizaSiniestro(polizaId: String): String? =
    if (polizaId.isBlank()) tr(R.string.siniestro_form_validation_selecciona_o_ingresa_la_poliza) else null

fun errorLugarSiniestro(lugar: String): String? {
    val limpio = lugar.trim()
    return when {
        limpio.isEmpty() -> tr(R.string.siniestro_form_validation_ingresa_el_lugar_del_evento)
        limpio.length > 200 -> tr(R.string.siniestro_form_validation_maximo_200_caracteres)
        else -> null
    }
}

fun errorDescripcionSiniestro(descripcion: String): String? {
    val limpia = descripcion.trim()
    return when {
        limpia.isEmpty() -> tr(R.string.siniestro_form_validation_describe_lo_que_paso)
        limpia.length < 10 -> tr(R.string.siniestro_form_validation_cuentanos_un_poco_mas_al)
        limpia.length > 2000 -> tr(R.string.siniestro_form_validation_maximo_2000_caracteres)
        else -> null
    }
}

fun errorEstimacionSiniestro(estimacion: String): String? {
    val limpia = estimacion.trim()
    return when {
        limpia.isEmpty() -> tr(R.string.siniestro_form_validation_ingresa_una_estimacion_del_dano)
        !formatoDecimal.matches(limpia) -> tr(R.string.siniestro_form_validation_usa_solo_numeros_maximo_2)
        else -> null
    }
}

fun errorHoraSiniestro(hora: String): String? {
    val limpia = hora.trim()
    return when {
        limpia.isEmpty() -> tr(R.string.siniestro_form_validation_ingresa_la_hora_del_evento)
        !formatoHora.matches(limpia) -> tr(R.string.siniestro_form_validation_usa_el_formato_hh_mm)
        else -> null
    }
}

fun errorFechaSiniestro(fecha: String, hoy: Calendar = Calendar.getInstance()): String? {
    val limpia = fecha.trim()
    if (limpia.isEmpty()) return tr(R.string.siniestro_form_validation_selecciona_la_fecha_del_evento)
    if (!formatoFechaIsoSiniestro.matches(limpia)) return tr(R.string.form_validation_usa_el_formato_aaaa_mm)
    val evento = Calendar.getInstance()
    try {
        val formato = SimpleDateFormat(FORMATO_FECHA, Locale.US).apply { isLenient = false }
        evento.time = formato.parse(limpia) ?: return tr(R.string.form_validation_fecha_no_valida)
    } catch (error: java.text.ParseException) {
        return tr(R.string.form_validation_fecha_no_valida)
    }
    // Se compara por día: el evento no puede estar en el futuro.
    val hoySoloFecha = (hoy.clone() as Calendar).apply {
        set(Calendar.HOUR_OF_DAY, 23)
        set(Calendar.MINUTE, 59)
        set(Calendar.SECOND, 59)
        set(Calendar.MILLISECOND, 999)
    }
    if (evento.after(hoySoloFecha)) return tr(R.string.siniestro_form_validation_la_fecha_no_puede_estar)
    return null
}

/** Normaliza la estimación a punto decimal para enviarla al backend. */
fun normalizarEstimacion(estimacion: String): String = estimacion.trim().replace(',', '.')

fun esFormularioSiniestroValido(
    polizaId: String,
    fecha: String,
    hora: String,
    lugar: String,
    descripcion: String,
    estimacion: String
): Boolean =
    errorPolizaSiniestro(polizaId) == null &&
        errorFechaSiniestro(fecha) == null &&
        errorHoraSiniestro(hora) == null &&
        errorLugarSiniestro(lugar) == null &&
        errorDescripcionSiniestro(descripcion) == null &&
        errorEstimacionSiniestro(estimacion) == null

/** HU04: el reporte pide el tipo de siniestro. */
fun errorTipoSiniestro(tipo: com.example.solventa.domain.siniestros.TipoSiniestro?): String? =
    if (tipo == null) tr(R.string.siniestro_form_validation_selecciona_el_tipo_de_siniestro) else null
