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
import com.example.solventa.domain.auth.RelojFalso
import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.BilleteraCoordinator
import com.example.solventa.domain.polizas.PolizasGatewayFalso
import com.example.solventa.ui.auth.AuthViewModel
import com.example.solventa.ui.billetera.BilleteraViewModel
import com.example.solventa.ui.screens.boton
import com.example.solventa.ui.screens.campo
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf

/** HU07: recorrido real desde el inicio hasta el certificado, con backends falsos. */
@RunWith(RobolectricTestRunner::class)
class NavGraphBilleteraTest {
    @get:Rule
    val compose = createComposeRule()

    private val gatewayAuth = GatewayFalso()
    private val gatewayPolizas = PolizasGatewayFalso()
    private lateinit var billetera: BilleteraViewModel
    private lateinit var actividad: FragmentActivity

    private fun mostrar() {
        val coordinador = AuthCoordinator(gatewayAuth, BovedaFalsa(), RelojFalso()) { false }
        val viewModel = AuthViewModel(coordinador)
        billetera = BilleteraViewModel(BilleteraCoordinator(gatewayPolizas, viewModel.sesion))
        actividad = Robolectric.buildActivity(FragmentActivity::class.java).setup().get()
        compose.setContent {
            SolventaTheme {
                NavGraph(
                    viewModel = viewModel,
                    autenticador = AutenticadorBiometrico(actividad),
                    billetera = billetera
                )
            }
        }
        compose.boton("Ingresar").performClick()
        compose.boton("Usar correo y contraseña").performClick()
        compose.campo("Correo electrónico").performTextInput("ana@gmail.com")
        compose.campo("Contraseña").performTextInput("clave123")
        compose.boton("Ingresar").performClick()
        compose.waitForIdle()
    }

    @Test
    fun desdeElInicioSeAbreLaBilleteraYElCertificado() {
        mostrar()

        compose.boton("Ver mi billetera").performClick()
        compose.waitForIdle()
        compose.onNodeWithText("Mi billetera").assertIsDisplayed()
        // El inicio consulta el resumen y la billetera vuelve a cargar la fuente de verdad.
        assertEquals(listOf("access-1", "access-1"), gatewayPolizas.tokensUsados)

        compose.boton("Seguro de viaje", substring = true).performClick()
        compose.waitForIdle()
        compose.onNodeWithContentDescription("Código QR de la póliza SOL-VJ-0001").assertIsDisplayed()
        assertEquals(listOf("POL-1"), gatewayPolizas.certificadosPedidos)

        compose.boton("Compartir certificado").performScrollTo().performClick()
        compose.waitForIdle()
        assertEquals(listOf("POL-1"), gatewayPolizas.compartidos)
        assertNull(billetera.estado.value.enlaceParaCompartir)
        val compartido = shadowOf(actividad.application).nextStartedActivity
        assertEquals("android.intent.action.CHOOSER", compartido?.action)

        compose.onNodeWithContentDescription("Volver").performClick()
        compose.waitForIdle()
        compose.onNodeWithText("Mi billetera").assertIsDisplayed()
        assertNull(billetera.estado.value.certificado)
    }

    @Test
    fun siElBackendRechazaElTokenVuelveAlIngresoYBorraLaBilletera() {
        mostrar()
        gatewayPolizas.respuestaBilletera = ResultadoApi.Fallo(401, "TOKEN_EXPIRED", null)

        compose.boton("Ver mi billetera").performClick()
        compose.waitForIdle()

        compose.onNodeWithText("Mi billetera").assertDoesNotExist()
        compose.onNodeWithText("Ver mi billetera").assertDoesNotExist()
        assertNull(billetera.estado.value.billetera)
    }
}
