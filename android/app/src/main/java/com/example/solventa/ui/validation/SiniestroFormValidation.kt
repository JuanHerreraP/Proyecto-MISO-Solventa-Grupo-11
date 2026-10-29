package com.example.solventa.ui.validation

import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

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
    if (polizaId.isBlank()) "Selecciona o ingresa la póliza afectada." else null

fun errorLugarSiniestro(lugar: String): String? {
    val limpio = lugar.trim()
    return when {
        limpio.isEmpty() -> "Ingresa el lugar del evento."
        limpio.length > 200 -> "Máximo 200 caracteres."
        else -> null
    }
}

fun errorDescripcionSiniestro(descripcion: String): String? {
    val limpia = descripcion.trim()
    return when {
        limpia.isEmpty() -> "Describe lo que pasó."
        limpia.length < 10 -> "Cuéntanos un poco más (al menos 10 caracteres)."
        limpia.length > 2000 -> "Máximo 2000 caracteres."
        else -> null
    }
}

fun errorEstimacionSiniestro(estimacion: String): String? {
    val limpia = estimacion.trim()
    return when {
        limpia.isEmpty() -> "Ingresa una estimación del daño."
        !formatoDecimal.matches(limpia) -> "Usa solo números (máximo 2 decimales)."
        else -> null
    }
}

fun errorHoraSiniestro(hora: String): String? {
    val limpia = hora.trim()
    return when {
        limpia.isEmpty() -> "Ingresa la hora del evento."
        !formatoHora.matches(limpia) -> "Usa el formato HH:MM (24 horas)."
        else -> null
    }
}

fun errorFechaSiniestro(fecha: String, hoy: Calendar = Calendar.getInstance()): String? {
    val limpia = fecha.trim()
    if (limpia.isEmpty()) return "Selecciona la fecha del evento."
    if (!formatoFechaIsoSiniestro.matches(limpia)) return "Usa el formato AAAA-MM-DD."
    val evento = Calendar.getInstance()
    try {
        val formato = SimpleDateFormat(FORMATO_FECHA, Locale.US).apply { isLenient = false }
        evento.time = formato.parse(limpia) ?: return "Fecha no válida."
    } catch (error: java.text.ParseException) {
        return "Fecha no válida."
    }
    // Se compara por día: el evento no puede estar en el futuro.
    val hoySoloFecha = (hoy.clone() as Calendar).apply {
        set(Calendar.HOUR_OF_DAY, 23)
        set(Calendar.MINUTE, 59)
        set(Calendar.SECOND, 59)
        set(Calendar.MILLISECOND, 999)
    }
    if (evento.after(hoySoloFecha)) return "La fecha no puede estar en el futuro."
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
