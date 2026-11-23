package com.example.solventa.e2e.autenticacion

import androidx.compose.ui.test.SemanticsNodeInteraction
import androidx.compose.ui.test.SemanticsNodeInteractionsProvider
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import com.example.solventa.E2ETestActivity
import com.example.solventa.biometric.AutenticadorBiometrico
import com.example.solventa.domain.auth.AuthCoordinator
import com.example.solventa.domain.auth.AuthGateway
import com.example.solventa.domain.auth.BovedaSesion
import com.example.solventa.domain.auth.DatosRegistro
import com.example.solventa.domain.auth.Perfil
import com.example.solventa.domain.auth.RegistroCreado
import com.example.solventa.domain.auth.Reloj
import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.auth.Tokens
import com.example.solventa.ui.auth.AuthViewModel
import com.example.solventa.ui.navigation.NavGraph
import com.example.solventa.ui.navigation.ScreenRoute
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import androidx.test.ext.junit.runners.AndroidJUnit4

/** Recorridos instrumentados de autenticación, ejecutados en emulador o dispositivo. */
@RunWith(AndroidJUnit4::class)
class AutenticacionE2ETest {
    @get:Rule
    val compose = createAndroidComposeRule<E2ETestActivity>()

    private val gateway = GatewayE2E()

    private fun mostrar(desde: String = ScreenRoute.Home.route) {
        compose.setContent {
            SolventaTheme {
                NavGraph(
                    viewModel = AuthViewModel(
                        AuthCoordinator(gateway, BovedaE2E(), RelojE2E()) { false }
                    ),
                    autenticador = AutenticadorBiometrico(compose.activity),
                    startDestination = desde
                )
            }
        }
    }

    @Test
    fun rutaPrivadaSinSesionRedirigeAlIngreso() {
        mostrar()

        compose.onNodeWithText("Hola de nuevo").assertIsDisplayed()
        compose.onNodeWithText(
            "Usa la huella configurada en tu dispositivo para entrar de forma rápida y segura."
        ).assertIsDisplayed()
    }

    @Test
    fun credencialesValidasAbrenPerfilYCerrarSesionProtegeLaCuenta() {
        mostrar()

        compose.boton("Usar correo y contraseña").performClick()
        compose.campo("Correo electrónico").performTextInput("ana@solventa.co")
        compose.campo("Contraseña").performTextInput("ClaveSegura123")
        compose.boton("Ingresar").performClick()

        compose.onNodeWithText("Hola, Ana").assertIsDisplayed()
        compose.onNodeWithContentDescription("Perfil").performClick()
        compose.boton("Cerrar sesión").performClick()

        compose.onNodeWithText("Hola de nuevo").assertIsDisplayed()
        compose.onNodeWithText("Cerraste sesión.").assertIsDisplayed()
    }
}

private fun SemanticsNodeInteractionsProvider.boton(texto: String): SemanticsNodeInteraction =
    onNode(hasText(texto) and hasClickAction())

private fun SemanticsNodeInteractionsProvider.campo(etiqueta: String): SemanticsNodeInteraction =
    onNode(hasSetTextAction() and hasText(etiqueta.uppercase(), substring = true))

private class GatewayE2E : AuthGateway {
    private val perfil = Perfil("e2e-ana", "Ana", "Pérez", "ana@solventa.co", "CLIENTE")

    override suspend fun registrar(datos: DatosRegistro) =
        ResultadoApi.Exito(RegistroCreado(datos.email, true))

    override suspend fun login(email: String, password: String) =
        ResultadoApi.Exito(Tokens("access-e2e", "refresh-e2e", 1_800))

    override suspend fun renovar(refreshToken: String) =
        ResultadoApi.Exito(Tokens("access-e2e-2", "refresh-e2e-2", 1_800))

    override suspend fun cerrarSesion(refreshToken: String) = ResultadoApi.Exito(Unit)

    override suspend fun perfil(accessToken: String) = ResultadoApi.Exito(perfil)
}

private class BovedaE2E : BovedaSesion {
    override fun tieneSesionGuardada() = false
    override fun preparar() = Unit
    override fun guardar(refreshToken: String) = Unit
    override fun leer(): String = error("No hay sesión biométrica en este recorrido")
    override fun borrar() = Unit
}

private class RelojE2E : Reloj {
    override fun ahoraMs(): Long = 1_000_000L
}
