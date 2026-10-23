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
import com.example.solventa.domain.cotizaciones.CotizacionesCoordinator
import com.example.solventa.domain.cotizaciones.CotizacionesGateway
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.example.solventa.domain.cotizaciones.ResultadoCotizacion
import com.example.solventa.ui.auth.AuthViewModel
import com.example.solventa.ui.cotizaciones.CotizacionDemostracion
import com.example.solventa.ui.cotizaciones.CotizacionesViewModel
import com.example.solventa.ui.screens.boton
import com.example.solventa.ui.screens.campo
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class NavGraphCotizacionesTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun navegaDelInicioAlListadoYAlDetalle() {
        val auth = AuthViewModel(
            AuthCoordinator(GatewayFalso(), BovedaFalsa(), RelojFalso()) { false }
        )
        val gateway = GatewayCotizacionesFalso()
        val cotizaciones = CotizacionesViewModel(
            CotizacionesCoordinator(gateway, auth.sesion)
        )
        val actividad = Robolectric.buildActivity(FragmentActivity::class.java).setup().get()
        compose.setContent {
            SolventaTheme {
                NavGraph(
                    viewModel = auth,
                    autenticador = AutenticadorBiometrico(actividad),
                    cotizaciones = cotizaciones
                )
            }
        }

        compose.boton("Ingresar").performClick()
        compose.boton("Usar correo y contraseña").performClick()
        compose.campo("Correo electrónico").performTextInput("ana@gmail.com")
        compose.campo("Contraseña").performTextInput("clave123")
        compose.boton("Ingresar").performClick()
        compose.waitForIdle()

        compose.boton("Ver cotizaciones").performScrollTo().performClick()
        compose.waitForIdle()
        compose.onNodeWithText("Mis cotizaciones").assertIsDisplayed()
        assertEquals(listOf("u-1"), gateway.clientesListados)

        compose.boton("Seguro de viaje").performClick()
        compose.waitForIdle()
        compose.onNodeWithText("Protección para tu viaje").assertIsDisplayed()

        compose.onNodeWithContentDescription("Volver").performClick()
        compose.waitForIdle()
        compose.onNodeWithText("Mis cotizaciones").assertIsDisplayed()
    }
}

private class GatewayCotizacionesFalso : CotizacionesGateway {
    val clientesListados = mutableListOf<String>()
    private val cotizacion = CotizacionDemostracion.para(RamoCotizacion.VIAJE)

    override suspend fun listar(
        accessToken: String,
        clienteId: String
    ): ResultadoApi<List<ResultadoCotizacion>> {
        clientesListados += clienteId
        return ResultadoApi.Exito(listOf(cotizacion))
    }

    override suspend fun cotizar(
        accessToken: String,
        clienteId: String,
        ramo: RamoCotizacion,
        datosRiesgo: Map<String, Any>
    ): ResultadoApi<ResultadoCotizacion> = ResultadoApi.Exito(cotizacion)
}
