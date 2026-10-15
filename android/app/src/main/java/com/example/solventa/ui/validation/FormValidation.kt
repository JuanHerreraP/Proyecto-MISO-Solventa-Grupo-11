package com.example.solventa.ui.validation

import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

fun canSubmitCredentialsLogin(email: String, password: String): Boolean =
    email.isNotBlank() && password.isNotBlank()

/** Tipos de documento que acepta el formulario: código enviado al backend y etiqueta visible. */
enum class TipoDocumento(val codigo: String, val etiqueta: String, val soloDigitos: Boolean) {
    CC("CC", "Cédula de ciudadanía", true),
    CE("CE", "Cédula de extranjería", true),
    TI("TI", "Tarjeta de identidad", true),
    PAS("PAS", "Pasaporte", false);

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
        limpio.isEmpty() -> "Ingresa tus $campo."
        limpio.length < 2 -> "Debe tener al menos 2 letras."
        limpio.length > 100 -> "Máximo 100 caracteres."
        !formatoNombre.matches(limpio) -> "Solo letras, espacios, guion o apóstrofe."
        else -> null
    }
}

fun errorTipoDocumento(codigo: String): String? =
    if (TipoDocumento.desdeCodigo(codigo) == null) "Selecciona un tipo de documento." else null

fun errorNumeroDocumento(tipo: String, numero: String): String? {
    val tipoDoc = TipoDocumento.desdeCodigo(tipo) ?: return "Primero selecciona el tipo de documento."
    val limpio = numero.trim()
    return when {
        limpio.isEmpty() -> "Ingresa el número de documento."
        tipoDoc.soloDigitos && !formatoDocumentoNumerico.matches(limpio) ->
            "Solo números, entre 5 y 12 dígitos."
        !tipoDoc.soloDigitos && !formatoPasaporte.matches(limpio) ->
            "Solo letras y números, entre 6 y 12 caracteres."
        else -> null
    }
}

fun errorCorreo(email: String): String? = when {
    email.isBlank() -> "Ingresa tu correo electrónico."
    !esCorreoValido(email) -> "Ingresa un correo electrónico válido."
    else -> null
}

fun errorCelular(celular: String): String? = when {
    celular.isBlank() -> "Ingresa tu número de celular."
    !formatoCelular.matches(celular.trim()) -> "Debe tener 10 dígitos y empezar por 3."
    else -> null
}

fun errorPassword(password: String): String? = when {
    password.isEmpty() -> "Crea una contraseña."
    password.length < 8 -> "Debe tener al menos 8 caracteres."
    password.length > 128 -> "Máximo 128 caracteres."
    password.none { it.isLetter() } -> "Debe incluir al menos una letra."
    password.none { it.isDigit() } -> "Debe incluir al menos un número."
    else -> null
}

fun errorFechaNacimiento(fecha: String, hoy: Calendar = Calendar.getInstance()): String? {
    val limpia = fecha.trim()
    if (limpia.isEmpty()) return "Selecciona tu fecha de nacimiento."
    if (!formatoFechaIso.matches(limpia)) return "Usa el formato AAAA-MM-DD."

    val nacimiento = Calendar.getInstance()
    try {
        val formato = SimpleDateFormat(FORMATO_FECHA, Locale.US).apply { isLenient = false }
        nacimiento.time = formato.parse(limpia) ?: return "Fecha no válida."
    } catch (error: java.text.ParseException) {
        return "Fecha no válida."
    }

    if (nacimiento.after(hoy)) return "La fecha no puede ser futura."

    var edad = hoy.get(Calendar.YEAR) - nacimiento.get(Calendar.YEAR)
    val aunNoCumple = hoy.get(Calendar.MONTH) < nacimiento.get(Calendar.MONTH) ||
        (hoy.get(Calendar.MONTH) == nacimiento.get(Calendar.MONTH) &&
            hoy.get(Calendar.DAY_OF_MONTH) < nacimiento.get(Calendar.DAY_OF_MONTH))
    if (aunNoCumple) edad--
    return when {
        edad < EDAD_MINIMA -> "Debes ser mayor de $EDAD_MINIMA años."
        edad > 120 -> "Fecha no válida."
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
