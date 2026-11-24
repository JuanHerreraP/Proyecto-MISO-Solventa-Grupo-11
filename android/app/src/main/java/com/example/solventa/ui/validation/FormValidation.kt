package com.example.solventa.ui.validation

import androidx.annotation.StringRes
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale
import com.example.solventa.R
import com.example.solventa.i18n.tr

fun canSubmitCredentialsLogin(email: String, password: String): Boolean =
    email.isNotBlank() && password.isNotBlank()

/** Tipos de documento que acepta el formulario: código enviado al backend y etiqueta visible. */
enum class TipoDocumento(val codigo: String, @StringRes private val etiquetaId: Int, val soloDigitos: Boolean) {
    CC("CC", R.string.form_validation_cedula_de_ciudadania, true),
    CE("CE", R.string.form_validation_cedula_de_extranjeria, true),
    TI("TI", R.string.form_validation_tarjeta_de_identidad, true),
    PAS("PAS", R.string.register_pasaporte, false);

    /** Etiqueta visible en el idioma activo. */
    val etiqueta: String get() = tr(etiquetaId)

    companion object {
        fun desdeCodigo(codigo: String): TipoDocumento? = entries.firstOrNull { it.codigo == codigo }
    }
}

const val EDAD_MINIMA = 18
const val FORMATO_FECHA = "yyyy-MM-dd"

private val formatoCorreo =
    Regex("^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")
private val formatoFechaIso = Regex("^\\d{4}-\\d{2}-\\d{2}$")
private val formatoNombre = Regex("^[\\p{L}]+([ '\\-][\\p{L}]+)*$")
private val formatoCelular = Regex("^3\\d{9}$")
private val formatoDocumentoNumerico = Regex("^\\d{5,12}$")
private val formatoPasaporte = Regex("^[A-Za-z0-9]{6,12}$")

fun esCorreoValido(email: String): Boolean = formatoCorreo.matches(email.trim())

/** Mensaje de error del campo, o null si el valor es válido. */
fun errorNombre(valor: String, campo: String): String? {
    val limpio = valor.trim()
    return when {
        limpio.isEmpty() -> tr(R.string.form_validation_ingresa_tus, campo)
        limpio.length < 2 -> tr(R.string.form_validation_debe_tener_al_menos_2)
        limpio.length > 100 -> tr(R.string.form_validation_maximo_100_caracteres)
        !formatoNombre.matches(limpio) -> tr(R.string.form_validation_solo_letras_espacios_guion_o)
        else -> null
    }
}

fun errorTipoDocumento(codigo: String): String? =
    if (TipoDocumento.desdeCodigo(codigo) == null) tr(R.string.form_validation_selecciona_un_tipo_de_documento) else null

fun errorNumeroDocumento(tipo: String, numero: String): String? {
    val tipoDoc = TipoDocumento.desdeCodigo(tipo) ?: return tr(R.string.form_validation_primero_selecciona_el_tipo_de)
    val limpio = numero.trim()
    return when {
        limpio.isEmpty() -> tr(R.string.form_validation_ingresa_el_numero_de_documento)
        tipoDoc.soloDigitos && !formatoDocumentoNumerico.matches(limpio) ->
            tr(R.string.form_validation_solo_numeros_entre_5_y)
        !tipoDoc.soloDigitos && !formatoPasaporte.matches(limpio) ->
            tr(R.string.form_validation_solo_letras_y_numeros_entre)
        else -> null
    }
}

fun errorCorreo(email: String): String? = when {
    email.isBlank() -> tr(R.string.form_validation_ingresa_tu_correo_electronico)
    !esCorreoValido(email) -> tr(R.string.form_validation_ingresa_un_correo_electronico_valido)
    else -> null
}

fun errorCelular(celular: String): String? = when {
    celular.isBlank() -> tr(R.string.form_validation_ingresa_tu_numero_de_celular)
    !formatoCelular.matches(celular.trim()) -> tr(R.string.form_validation_debe_tener_10_digitos_y)
    else -> null
}

fun errorPassword(password: String): String? = when {
    password.isEmpty() -> tr(R.string.form_validation_crea_una_contrasena)
    password.length < 8 -> tr(R.string.form_validation_debe_tener_al_menos_8)
    password.length > 128 -> tr(R.string.form_validation_maximo_128_caracteres)
    password.none { it.isLetter() } -> tr(R.string.form_validation_debe_incluir_al_menos_una)
    password.none { it.isDigit() } -> tr(R.string.form_validation_debe_incluir_al_menos_un)
    else -> null
}

fun errorFechaNacimiento(fecha: String, hoy: Calendar = Calendar.getInstance()): String? {
    val limpia = fecha.trim()
    if (limpia.isEmpty()) return tr(R.string.form_validation_selecciona_tu_fecha_de_nacimiento)
    if (!formatoFechaIso.matches(limpia)) return tr(R.string.form_validation_usa_el_formato_aaaa_mm)

    val nacimiento = Calendar.getInstance()
    try {
        val formato = SimpleDateFormat(FORMATO_FECHA, Locale.US).apply { isLenient = false }
        nacimiento.time = formato.parse(limpia) ?: return tr(R.string.form_validation_fecha_no_valida)
    } catch (error: java.text.ParseException) {
        return tr(R.string.form_validation_fecha_no_valida)
    }

    if (nacimiento.after(hoy)) return tr(R.string.form_validation_la_fecha_no_puede_ser)

    var edad = hoy.get(Calendar.YEAR) - nacimiento.get(Calendar.YEAR)
    val aunNoCumple = hoy.get(Calendar.MONTH) < nacimiento.get(Calendar.MONTH) ||
        (hoy.get(Calendar.MONTH) == nacimiento.get(Calendar.MONTH) &&
            hoy.get(Calendar.DAY_OF_MONTH) < nacimiento.get(Calendar.DAY_OF_MONTH))
    if (aunNoCumple) edad--
    return when {
        edad < EDAD_MINIMA -> tr(R.string.form_validation_debes_ser_mayor_de_anos, EDAD_MINIMA)
        edad > 120 -> tr(R.string.form_validation_fecha_no_valida)
        else -> null
    }
}

fun esFormularioRegistroValido(
    nombre: String,
    apellido: String,
    tipoDocumento: String,
    numeroDocumento: String,
    email: String,
    celular: String,
    password: String,
    fechaNacimiento: String,
    termsAccepted: Boolean
): Boolean =
    errorNombre(nombre, "nombres") == null &&
        errorNombre(apellido, "apellidos") == null &&
        errorTipoDocumento(tipoDocumento) == null &&
        errorNumeroDocumento(tipoDocumento, numeroDocumento) == null &&
        errorCorreo(email) == null &&
        errorCelular(celular) == null &&
        errorPassword(password) == null &&
        errorFechaNacimiento(fechaNacimiento) == null &&
        termsAccepted

fun canSubmitRegistration(
    nombre: String,
    apellido: String,
    tipoDocumento: String,
    numeroDocumento: String,
    email: String,
    celular: String,
    password: String,
    fechaNacimiento: String,
    termsAccepted: Boolean,
    selfieCaptured: Boolean
): Boolean =
    esFormularioRegistroValido(
        nombre,
        apellido,
        tipoDocumento,
        numeroDocumento,
        email,
        celular,
        password,
        fechaNacimiento,
        termsAccepted
    ) && selfieCaptured
