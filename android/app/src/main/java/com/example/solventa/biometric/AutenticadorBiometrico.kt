package com.example.solventa.biometric

import androidx.biometric.BiometricManager
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_STRONG
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity

/**
 * Envuelve [BiometricPrompt]. La huella o el rostro se validan en el dispositivo;
 * Solventa solo recibe el resultado.
 */
class AutenticadorBiometrico(private val actividad: FragmentActivity) {

    fun disponibilidad(): DisponibilidadBiometrica =
        mapearDisponibilidad(BiometricManager.from(actividad).canAuthenticate(BIOMETRIC_STRONG))

    fun autenticar(
        titulo: String,
        subtitulo: String,
        alExito: () -> Unit,
        alFallo: (FalloBiometrico) -> Unit,
        alNoCoincidir: () -> Unit
    ) {
        val callback = object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                alExito()
            }

            override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                alFallo(mapearErrorBiometrico(errorCode, errString))
            }

            override fun onAuthenticationFailed() {
                // La huella no coincidió; el diálogo sigue abierto para otro intento.
                alNoCoincidir()
            }
        }

        val informacion = BiometricPrompt.PromptInfo.Builder()
            .setTitle(titulo)
            .setSubtitle(subtitulo)
            .setNegativeButtonText("Usar correo y contraseña")
            .setAllowedAuthenticators(BIOMETRIC_STRONG)
            .setConfirmationRequired(false)
            .build()

        BiometricPrompt(actividad, ContextCompat.getMainExecutor(actividad), callback)
            .authenticate(informacion)
    }
}
