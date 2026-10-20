package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/** Pantallas de bienvenida, ingreso biométrico e ingreso con credenciales. */
@RunWith(RobolectricTestRunner::class)
class PantallasDeIngresoTest {
    @get:Rule
    val compose = createComposeRule()

    private val eventos = mutableListOf<String>()

    // --- Bienvenida ---

    @Test
    fun bienvenidaLlevaAIngresarYARegistrarse() {
        compose.setContent {
            SolventaTheme {
                WelcomeScreen(
                    onLoginClick = { eventos += "ingresar" },
                    onRegisterClick = { eventos += "registrar" }
                )
            }
        }

        compose.onNodeWithText("Identidad verificada y datos protegidos").assertIsDisplayed()
        compose.boton("Ingresar").performClick()
        compose.boton("Crear una cuenta").performClick()

        assertEquals(listOf("ingresar", "registrar"), eventos)
    }

    // --- Ingreso biométrico ---

    private fun mostrarBiometrico(
        disponible: Boolean = true,
        cargando: Boolean = false,
        mensaje: String? = null
    ) {
        compose.setContent {
            SolventaTheme {
                BiometricalLoginScreen(
                    onBackClick = { eventos += "volver" },
                    onBiometricClick = { eventos += "huella" },
                    onUseCredentialsClick = { eventos += "credenciales" },
                    onRegisterClick = { eventos += "registrar" },
                    biometriaDisponible = disponible,
                    cargando = cargando,
                    mensaje = mensaje
                )
            }
        }
    }

    @Test
    fun ingresoBiometricoNotificaCadaAccion() {
        mostrarBiometrico()

        compose.onNodeWithText("Hola de nuevo").assertIsDisplayed()
        compose.boton("Ingresar con biometría").assertIsEnabled().performClick()
        compose.boton("Usar correo y contraseña").performClick()
        compose.boton("Crear una", substring = true).performClick()
        compose.onNodeWithContentDescription("Volver").performClick()

        assertEquals(listOf("huella", "credenciales", "registrar", "volver"), eventos)
    }

    @Test
    fun sinBiometriaElBotonDeHuellaQuedaDeshabilitadoYSeMuestraElMotivo() {
        mostrarBiometrico(disponible = false, mensaje = "Este dispositivo no tiene lector biométrico.")

        compose.boton("Ingresar con biometría").assertIsNotEnabled()
        compose.onNodeWithText("Este dispositivo no tiene lector biométrico.").assertIsDisplayed()
    }

    @Test
    fun mientrasCargaNoSePuedePedirLaHuellaOtraVez() {
        mostrarBiometrico(cargando = true)

        compose.onNodeWithText("Ingresar con biometría").assertDoesNotExist()
    }

    // --- Ingreso con credenciales ---

    private var enviado: Pair<String, String>? = null

    private fun mostrarCredenciales(cargando: Boolean = false, mensaje: String? = null) {
        compose.setContent {
            SolventaTheme {
                CredentialsLoginScreen(
                    onBackClick = { eventos += "volver" },
                    onLoginSubmit = { email, clave -> enviado = email to clave },
                    onSwitchToBiometric = { eventos += "huella" },
                    onForgotPasswordClick = { eventos += "olvido" },
                    cargando = cargando,
                    mensaje = mensaje
                )
            }
        }
    }

    @Test
    fun ingresarSoloSeHabilitaConCorreoYContrasena() {
        mostrarCredenciales()

        compose.boton("Ingresar").assertIsNotEnabled()
        compose.campo("Correo electrónico").performTextInput("ana@gmail.com")
        compose.boton("Ingresar").assertIsNotEnabled()
        compose.campo("Contraseña").performTextInput("clave123")
        compose.boton("Ingresar").assertIsEnabled().performClick()

        assertEquals("ana@gmail.com" to "clave123", enviado)
    }

    @Test
    fun credencialesNotificanLasDemasAcciones() {
        mostrarCredenciales()

        compose.boton("Usar ingreso biométrico").performClick()
        compose.boton("¿Olvidaste tu contraseña?").performClick()
        compose.onNodeWithContentDescription("Volver").performClick()

        assertEquals(listOf("huella", "olvido", "volver"), eventos)
    }

    @Test
    fun credencialesMuestranElMensajeDeError() {
        mostrarCredenciales(mensaje = "El correo electrónico o la contraseña son incorrectos.")

        compose.onNodeWithText("El correo electrónico o la contraseña son incorrectos.").assertIsDisplayed()
        compose.onNodeWithText("Nunca compartas tu contraseña ni códigos de verificación.").assertIsDisplayed()
    }

    @Test
    fun mientrasCargaElBotonIngresarMuestraElProgreso() {
        mostrarCredenciales(cargando = true)

        compose.boton("Ingresar").assertDoesNotExist()
        compose.onNodeWithText("Accede a tu cuenta").assertIsDisplayed()
    }
}
