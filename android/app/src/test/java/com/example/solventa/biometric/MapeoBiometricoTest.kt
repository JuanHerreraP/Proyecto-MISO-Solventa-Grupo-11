package com.example.solventa.biometric

import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class MapeoBiometricoTest {
    @Test
    fun dispositivoConBiometriaFuerteEstaDisponible() {
        assertEquals(
            DisponibilidadBiometrica.DISPONIBLE,
            mapearDisponibilidad(BiometricManager.BIOMETRIC_SUCCESS)
        )
        assertNull(DisponibilidadBiometrica.DISPONIBLE.mensaje())
    }

    @Test
    fun dispositivoSinBiometriaOfreceCredenciales() {
        val casos = mapOf(
            BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED to DisponibilidadBiometrica.NO_CONFIGURADA,
            BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE to DisponibilidadBiometrica.SIN_HARDWARE,
            BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE to DisponibilidadBiometrica.NO_DISPONIBLE_TEMPORALMENTE,
            BiometricManager.BIOMETRIC_ERROR_SECURITY_UPDATE_REQUIRED to DisponibilidadBiometrica.NO_SOPORTADA,
            BiometricManager.BIOMETRIC_ERROR_UNSUPPORTED to DisponibilidadBiometrica.NO_SOPORTADA
        )

        casos.forEach { (codigo, esperado) ->
            val disponibilidad = mapearDisponibilidad(codigo)
            assertEquals(esperado, disponibilidad)
            assertNotNull(disponibilidad.mensaje())
        }
    }

    @Test
    fun bloqueoPorIntentosSeTraduceABloqueado() {
        assertEquals(FalloBiometrico.Bloqueado, mapearErrorBiometrico(BiometricPrompt.ERROR_LOCKOUT, "x"))
        assertEquals(
            FalloBiometrico.Bloqueado,
            mapearErrorBiometrico(BiometricPrompt.ERROR_LOCKOUT_PERMANENT, "x")
        )
    }

    @Test
    fun biometriaDeshabilitadaSeTraduceANoDisponible() {
        listOf(
            BiometricPrompt.ERROR_HW_UNAVAILABLE,
            BiometricPrompt.ERROR_HW_NOT_PRESENT,
            BiometricPrompt.ERROR_NO_BIOMETRICS
        ).forEach { codigo ->
            assertEquals(FalloBiometrico.NoDisponible, mapearErrorBiometrico(codigo, "x"))
        }
    }

    @Test
    fun botonNegativoLlevaACredenciales() {
        assertEquals(
            FalloBiometrico.UsarCredenciales,
            mapearErrorBiometrico(BiometricPrompt.ERROR_NEGATIVE_BUTTON, "Usar correo")
        )
    }

    @Test
    fun cancelarNoEsUnError() {
        assertEquals(FalloBiometrico.Cancelado, mapearErrorBiometrico(BiometricPrompt.ERROR_USER_CANCELED, ""))
        assertEquals(FalloBiometrico.Cancelado, mapearErrorBiometrico(BiometricPrompt.ERROR_CANCELED, ""))
    }

    @Test
    fun erroresTransitoriosPermitenReintentar() {
        assertEquals(
            FalloBiometrico.Reintentable("Tiempo agotado"),
            mapearErrorBiometrico(BiometricPrompt.ERROR_TIMEOUT, "Tiempo agotado")
        )
        assertEquals(
            FalloBiometrico.Reintentable("No pudimos validar tu huella. Inténtalo de nuevo."),
            mapearErrorBiometrico(BiometricPrompt.ERROR_UNABLE_TO_PROCESS, " ")
        )
    }
}
