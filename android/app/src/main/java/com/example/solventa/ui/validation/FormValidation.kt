package com.example.solventa.ui.validation

fun canSubmitCredentialsLogin(email: String, password: String): Boolean =
    email.isNotBlank() && password.isNotBlank()

private val formatoCorreo =
    Regex("^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")
private val formatoFechaIso = Regex("^\\d{4}-\\d{2}-\\d{2}$")

fun esCorreoValido(email: String): Boolean = formatoCorreo.matches(email.trim())

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
    nombre.trim().length >= 2 &&
        apellido.trim().length >= 2 &&
        tipoDocumento.isNotBlank() &&
        numeroDocumento.isNotBlank() &&
        esCorreoValido(email) &&
        celular.isNotBlank() &&
        password.length >= 8 &&
        formatoFechaIso.matches(fechaNacimiento.trim()) &&
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
