package com.example.solventa.ui.navigation

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.fragment.app.FragmentActivity
import com.example.solventa.biometric.AutenticadorBiometrico
import com.example.solventa.domain.auth.AuthCoordinator
import com.example.solventa.domain.auth.BovedaFalsa
import com.example.solventa.domain.auth.GatewayFalso
import com.example.solventa.domain.auth.MensajesAuth
import com.example.solventa.domain.auth.RelojFalso
import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.ui.auth.AuthViewModel
import com.example.solventa.ui.screens.boton
import com.example.solventa.ui.screens.campo
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner

/** Recorre la navegación real de la app con un backend y una bóveda falsos. */
@RunWith(RobolectricTestRunner::class)
class NavGraphTest {
    @get:Rule
    val compose = createComposeRule()

    private val gateway = GatewayFalso()

    private fun mostrar(boveda: BovedaFalsa = BovedaFalsa()) {
        val coordinador = AuthCoordinator(gateway, boveda, RelojFalso()) { false }
        val viewModel = AuthViewModel(coordinador)
        val actividad = Robolectric.buildActivity(FragmentActivity::class.java).setup().get()
        compose.setContent {
            SolventaTheme {
                NavGraph(viewModel = viewModel, autenticador = AutenticadorBiometrico(actividad))
            }
        }
    }

    private fun ingresarConCredenciales() {
        compose.boton("Usar correo y contraseña").performClick()
        compose.campo("Correo electrónico").performTextInput("ana@gmail.com")
        compose.campo("Contraseña").performTextInput("clave123")
        compose.boton("Ingresar").performClick()
        compose.waitForIdle()
    }

    @Test
    fun desdeLaBienvenidaSeIngresaConCredencialesYSeCierraSesion() {
        mostrar()

        compose.boton("Ingresar").performClick()
        compose.onNodeWithText("Hola de nuevo").assertIsDisplayed()

        ingresarConCredenciales()
        compose.onNodeWithText("Hola, Ana").assertIsDisplayed()

        compose.boton("Cerrar sesión").performClick()
        compose.waitForIdle()

        compose.onNodeWithText("Hola de nuevo").assertIsDisplayed()
        compose.onNodeWithText(MensajesAuth.SESION_CERRADA).assertIsDisplayed()
    }

    @Test
    fun entrarConCredencialesReemplazaLaSesionGuardada() {
        val boveda = BovedaFalsa(guardado = "refresh-0")
        mostrar(boveda)

        compose.boton("Ingresar").performClick()
        // Entrar con credenciales reemplaza la sesión guardada anterior.
        ingresarConCredenciales()
        compose.onNodeWithText("Ingreso con huella desactivado").assertIsDisplayed()
    }

    @Test
    fun desdeLaBienvenidaSeAbreElRegistroYSePuedeVolverAlIngreso() {
        mostrar()

        compose.boton("Crear una cuenta").performClick()
        compose.onNodeWithText("Cuéntanos sobre ti").assertIsDisplayed()

        compose.boton("¿Ya tienes cuenta? Iniciar sesión").performScrollTo().performClick()
        compose.onNodeWithText("Hola de nuevo").assertIsDisplayed()
    }

    @Test
    fun desdeElIngresoBiometricoSePuedeIrAlRegistroYVolver() {
        mostrar()
        compose.boton("Ingresar").performClick()

        compose.boton("Crear una", substring = true).performClick()
        compose.onNodeWithText("Cuéntanos sobre ti").assertIsDisplayed()

        compose.onNodeWithContentDescription("Volver").performClick()
        compose.onNodeWithText("Hola de nuevo").assertIsDisplayed()
    }

    @Test
    fun desdeLasCredencialesSeVuelveAlIngresoBiometrico() {
        mostrar()
        compose.boton("Ingresar").performClick()
        compose.boton("Usar correo y contraseña").performClick()
        compose.onNodeWithText("Accede a tu cuenta").assertIsDisplayed()

        compose.boton("Usar ingreso biométrico").performClick()
        compose.onNodeWithText("Hola de nuevo").assertIsDisplayed()

        compose.boton("Usar correo y contraseña").performClick()
        compose.onNodeWithContentDescription("Volver").performClick()
        compose.onNodeWithText("Hola de nuevo").assertIsDisplayed()
    }

    @Test
    fun elBotonVolverDelIngresoBiometricoRegresaALaBienvenida() {
        mostrar()
        compose.boton("Ingresar").performClick()

        compose.onNodeWithContentDescription("Volver").performClick()

        compose.onNodeWithText("Identidad verificada y datos protegidos").assertIsDisplayed()
    }

    @Test
    fun credencialesInvalidasMuestranElErrorSinEntrar() {
        gateway.respuestaLogin = ResultadoApi.Fallo(401, null, null)
        mostrar()
        compose.boton("Ingresar").performClick()

        ingresarConCredenciales()

        compose.onNodeWithText(MensajesAuth.CREDENCIALES_INVALIDAS).assertIsDisplayed()
    }
}
