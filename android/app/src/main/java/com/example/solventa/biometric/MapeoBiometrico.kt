package com.example.solventa.biometric

import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt

enum class DisponibilidadBiometrica {
    DISPONIBLE,
    NO_CONFIGURADA,
    SIN_HARDWARE,
    NO_DISPONIBLE_TEMPORALMENTE,
    NO_SOPORTADA
}

/** Traduce el código de [BiometricManager.canAuthenticate] (BIOMETRIC_STRONG). */
fun mapearDisponibilidad(codigo: Int): DisponibilidadBiometrica = when (codigo) {
    BiometricManager.BIOMETRIC_SUCCESS -> DisponibilidadBiometrica.DISPONIBLE
    BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> DisponibilidadBiometrica.NO_CONFIGURADA
    BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> DisponibilidadBiometrica.SIN_HARDWARE
    BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE -> DisponibilidadBiometrica.NO_DISPONIBLE_TEMPORALMENTE
    else -> DisponibilidadBiometrica.NO_SOPORTADA
}

/** Mensaje para la pantalla de ingreso; null cuando la biometría se puede usar. */
fun DisponibilidadBiometrica.mensaje(): String? = when (this) {
    DisponibilidadBiometrica.DISPONIBLE -> null
    DisponibilidadBiometrica.NO_CONFIGURADA ->
        "No tienes huella ni rostro configurados en el dispositivo. Ingresa con tu correo y contraseña."
    DisponibilidadBiometrica.SIN_HARDWARE ->
        "Este dispositivo no tiene lector biométrico. Ingresa con tu correo y contraseña."
    DisponibilidadBiometrica.NO_DISPONIBLE_TEMPORALMENTE ->
        "La biometría no está disponible en este momento. Ingresa con tu correo y contraseña."
    DisponibilidadBiometrica.NO_SOPORTADA ->
        "La biometría de este dispositivo no cumple el nivel de seguridad requerido. Ingresa con tu correo y contraseña."
}

/** Cómo debe reaccionar la app cuando el diálogo biométrico termina con error. */
sealed interface FalloBiometrico {
    /** Demasiados intentos: el dispositivo bloqueó la biometría. */
    data object Bloqueado : FalloBiometrico

    /** No hay hardware, no hay huellas registradas o requiere actualización. */
    data object NoDisponible : FalloBiometrico

    /** El usuario pulsó "Usar correo y contraseña". */
    data object UsarCredenciales : FalloBiometrico

    /** El usuario cerró el diálogo. */
    data object Cancelado : FalloBiometrico

    /** Error transitorio (tiempo agotado, sensor ocupado): se puede volver a intentar. */
    data class Reintentable(val mensaje: String) : FalloBiometrico
}

/** Traduce el código de [BiometricPrompt.AuthenticationCallback.onAuthenticationError]. */
fun mapearErrorBiometrico(codigo: Int, mensaje: CharSequence?): FalloBiometrico = when (codigo) {
    BiometricPrompt.ERROR_LOCKOUT,
    BiometricPrompt.ERROR_LOCKOUT_PERMANENT -> FalloBiometrico.Bloqueado

    BiometricPrompt.ERROR_HW_UNAVAILABLE,
    BiometricPrompt.ERROR_HW_NOT_PRESENT,
    BiometricPrompt.ERROR_NO_BIOMETRICS,
    BiometricPrompt.ERROR_SECURITY_UPDATE_REQUIRED -> FalloBiometrico.NoDisponible

    BiometricPrompt.ERROR_NEGATIVE_BUTTON -> FalloBiometrico.UsarCredenciales

    BiometricPrompt.ERROR_USER_CANCELED,
    BiometricPrompt.ERROR_CANCELED -> FalloBiometrico.Cancelado

    else -> FalloBiometrico.Reintentable(
        mensaje?.toString()?.takeIf { it.isNotBlank() }
            ?: "No pudimos validar tu huella. Inténtalo de nuevo."
    )
}
