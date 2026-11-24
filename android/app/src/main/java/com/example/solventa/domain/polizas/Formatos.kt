package com.example.solventa.domain.polizas

import java.math.BigDecimal
import java.math.RoundingMode
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

/**
 * Formatos de la billetera. No usan java.time porque la app soporta desde API 24
 * sin desugaring; así también se prueban en la JVM sin Android.
 */
object Formatos {
    private val MESES = listOf(
        "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"
    )
    private val MESES_EN = listOf(
        "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    )

    /**
     * Formatos en inglés (en-US) en lugar de español de Colombia. Lo ajusta la capa de UI
     * (i18n.Idioma) al cambiar el idioma de la app; el dominio no depende de Android.
     */
    @Volatile
    var ingles: Boolean = false

    /** "1 oct 2026" en español; "Oct 1, 2026" en inglés. */
    private fun diaMesAnio(dia: Int, mes: Int, anio: Int): String =
        if (ingles) "${MESES_EN[mes]} $dia, $anio" else "$dia ${MESES[mes]} $anio"

    /** "2026-10-01" → "1 oct 2026". Si no es una fecha ISO, la devuelve igual. */
    fun fecha(iso: String): String {
        val partes = iso.take(10).split("-")
        if (partes.size != 3) return iso
        val anio = partes[0].toIntOrNull()
        val mes = partes[1].toIntOrNull()
        val dia = partes[2].toIntOrNull()
        if (anio == null || mes == null || dia == null || mes !in 1..12 || dia !in 1..31) return iso
        return diaMesAnio(dia, mes - 1, anio)
    }

    fun vigencia(inicio: String, fin: String): String = "${fecha(inicio)} – ${fecha(fin)}"

    /**
     * "2026-10-22T15:00:00.123456Z" o con "+00:00" → "22 oct 2026, 10:00" en la zona indicada.
     * Si no se puede leer, devuelve el texto original.
     */
    fun fechaHora(iso: String, zona: TimeZone = TimeZone.getDefault()): String {
        val normalizado = normalizarIso(iso) ?: return iso
        return try {
            val lector = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssZ", Locale.US).apply {
                isLenient = false
            }
            val instante = lector.parse(normalizado) ?: return iso
            fechaHora(instante.time, zona)
        } catch (error: java.text.ParseException) {
            iso
        }
    }

    /** Epoch milliseconds → "22 oct 2026, 10:00" en la zona del dispositivo. */
    fun fechaHora(instanteMs: Long, zona: TimeZone = TimeZone.getDefault()): String {
        val calendario = java.util.Calendar.getInstance(zona).apply { timeInMillis = instanteMs }
        val dia = calendario.get(java.util.Calendar.DAY_OF_MONTH)
        val mes = calendario.get(java.util.Calendar.MONTH)
        val anio = calendario.get(java.util.Calendar.YEAR)
        val hora = calendario.get(java.util.Calendar.HOUR_OF_DAY).toString().padStart(2, '0')
        val minuto = calendario.get(java.util.Calendar.MINUTE).toString().padStart(2, '0')
        return "${diaMesAnio(dia, mes, anio)}, $hora:$minuto"
    }

    /** Epoch milliseconds → "22 oct 2026, 10:00 AM" en la zona del dispositivo. */
    fun fechaHoraDoceHoras(instanteMs: Long, zona: TimeZone = TimeZone.getDefault()): String {
        val calendario = java.util.Calendar.getInstance(zona).apply { timeInMillis = instanteMs }
        val dia = calendario.get(java.util.Calendar.DAY_OF_MONTH)
        val mes = calendario.get(java.util.Calendar.MONTH)
        val anio = calendario.get(java.util.Calendar.YEAR)
        val hora24 = calendario.get(java.util.Calendar.HOUR_OF_DAY)
        val hora12 = when (val hora = hora24 % 12) {
            0 -> 12
            else -> hora
        }
        val minuto = calendario.get(java.util.Calendar.MINUTE).toString().padStart(2, '0')
        val periodo = if (hora24 < 12) "AM" else "PM"
        return "${diaMesAnio(dia, mes, anio)}, $hora12:$minuto $periodo"
    }

    /** "40000000.00" con COP → "$40.000.000"; con centavos, "$1.234,50". */
    fun dinero(valor: String, moneda: String): String {
        val numero = valor.toBigDecimalOrNull() ?: return "$moneda $valor"
        val redondeado = numero.setScale(2, RoundingMode.HALF_UP)
        val entero = redondeado.toBigInteger().abs().toString()
        // Separadores: es-CO usa punto de miles y coma decimal; en-US, al revés.
        val (miles, decimal) = if (ingles) "," to "." else "." to ","
        val agrupado = entero.reversed().chunked(3).joinToString(miles).reversed()
        val centavos = redondeado.remainder(BigDecimal.ONE).abs().movePointRight(2).toInt()
        val signo = if (redondeado.signum() < 0) "-" else ""
        val simbolo = if (moneda == "COP" || moneda == "USD") "$" else "$moneda "
        val decimales = if (centavos == 0) "" else "$decimal${centavos.toString().padStart(2, '0')}"
        return "$signo$simbolo$agrupado$decimales"
    }

    fun estado(estado: EstadoPoliza): String = when (estado) {
        EstadoPoliza.VIGENTE -> if (ingles) "Active" else "Vigente"
        EstadoPoliza.VENCIDA -> if (ingles) "Expired" else "Vencida"
        EstadoPoliza.CANCELADA -> if (ingles) "Cancelled" else "Cancelada"
    }

    private fun normalizarIso(iso: String): String? {
        val coincidencia = Regex(
            """^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:?\d{2})$"""
        ).matchEntire(iso.trim()) ?: return null
        val base = coincidencia.groupValues[1]
        val zona = coincidencia.groupValues[3]
        val offset = if (zona == "Z") "+0000" else zona.replace(":", "")
        return base + offset
    }
}
