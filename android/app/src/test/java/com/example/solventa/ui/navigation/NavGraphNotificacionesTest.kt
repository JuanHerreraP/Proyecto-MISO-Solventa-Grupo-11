package com.example.solventa.ui.navigation

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithContentDescription
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.fragment.app.FragmentActivity
import com.example.solventa.biometric.AutenticadorBiometrico
import com.example.solventa.domain.auth.AuthCoordinator
import com.example.solventa.domain.auth.BovedaFalsa
import com.example.solventa.domain.auth.GatewayFalso
import com.example.solventa.domain.auth.RelojFalso
import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.notificaciones.Bandeja
import com.example.solventa.domain.notificaciones.DestinoNotificacion
import com.example.solventa.domain.notificaciones.GatewayNotificacionesFalso
import com.example.solventa.domain.notificaciones.NotificacionesCoordinator
import com.example.solventa.domain.notificaciones.ProveedorTokenFalso
import com.example.solventa.domain.notificaciones.notificacion
import com.example.solventa.domain.siniestros.EstadoSiniestro
import com.example.solventa.domain.siniestros.OrigenSiniestro
import com.example.solventa.domain.siniestros.SiniestrosCoordinator
import com.example.solventa.domain.siniestros.SiniestrosGatewayFalso
import com.example.solventa.domain.siniestros.siniestro
import com.example.solventa.domain.siniestros.siniestrosDe
import com.example.solventa.ui.auth.AuthViewModel
import com.example.solventa.ui.notificaciones.AperturaNotificacion
import com.example.solventa.ui.notificaciones.NotificacionesViewModel
import com.example.solventa.ui.screens.boton
import com.example.solventa.ui.screens.campo
import com.example.solventa.ui.siniestros.SiniestrosViewModel
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner

/** HU05: recorrido real de las notificaciones (bandeja, apertura, preferencia y baja del teléfono). */
@RunWith(RobolectricTestRunner::class)
class NavGraphNotificacionesTest {
    @get:Rule
    val compose = createComposeRule()

    private val gatewayAuth = GatewayFalso()
    private val gatewayNotificaciones = GatewayNotificacionesFalso()
    private val gatewaySiniestros = SiniestrosGatewayFalso()
    private val proveedor = ProveedorTokenFalso("tok-1")
    private var apertura by mutableStateOf<AperturaNotificacion?>(null)
    private var aperturasConsumidas = 0

    private fun mostrar(aperturaInicial: AperturaNotificacion? = null) {
        apertura = aperturaInicial
        gatewaySiniestros.respuesta = ResultadoApi.Exito(
            siniestrosDe(
                siniestro(id = "SIN-1", origen = OrigenSiniestro.MANUAL, estado = EstadoSiniestro.EN_EVALUACION)
            )
        )
        val coordinador = AuthCoordinator(gatewayAuth, BovedaFalsa(), RelojFalso()) { false }
        val viewModel = AuthViewModel(coordinador)
        val notificaciones = NotificacionesViewModel(
            NotificacionesCoordinator(gatewayNotificaciones, viewModel.sesion, proveedor)
        )
        val siniestros = SiniestrosViewModel(SiniestrosCoordinator(gatewaySiniestros, viewModel.sesion))
        val actividad = Robolectric.buildActivity(FragmentActivity::class.java).setup().get()
        compose.setContent {
            SolventaTheme {
                NavGraph(
                    viewModel = viewModel,
                    autenticador = AutenticadorBiometrico(actividad),
                    siniestros = siniestros,
                    notificaciones = notificaciones,
                    aperturaPendiente = apertura,
                    onAperturaConsumida = {
                        aperturasConsumidas++
                        apertura = null
                    }
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

    private fun esperarTexto(descripcion: String) {
        compose.waitUntil(timeoutMillis = 5_000) {
            compose.onAllNodesWithContentDescription(descripcion).fetchSemanticsNodes().isNotEmpty()
        }
    }

    @Test
    fun alIniciarSesionSeRegistraElTelefonoYLaCampanaMuestraLasNoLeidas() {
        gatewayNotificaciones.conteo = ResultadoApi.Exito(1)

        mostrar()
        esperarTexto("Notificaciones, 1 sin leer")

        assertEquals(listOf("tok-1"), gatewayNotificaciones.registrados)
        compose.onNodeWithContentDescription("Notificaciones, 1 sin leer").assertIsDisplayed()
    }

    @Test
    fun desdeLaBandejaUnaNotificacionAbreElDetalleYQuedaLeida() {
        gatewayNotificaciones.conteo = ResultadoApi.Exito(1)
        gatewayNotificaciones.bandeja = ResultadoApi.Exito(
            Bandeja(listOf(notificacion("N-1")), noLeidas = 1)
        )
        mostrar()
        esperarTexto("Notificaciones, 1 sin leer")

        compose.onNodeWithContentDescription("Notificaciones, 1 sin leer").performClick()
        compose.waitForIdle()
        compose.onNodeWithText("Título N-1").performClick()
        compose.waitForIdle()

        compose.onNodeWithText("Siniestro SIN-1").assertIsDisplayed()
        compose.onNodeWithText("Evaluación en curso").assertIsDisplayed()
        assertEquals(listOf("N-1"), gatewayNotificaciones.leidas)
    }

    @Test
    fun unaAperturaPendienteAbreElDetalleDespuesDeIniciarSesion() {
        mostrar(
            AperturaNotificacion(DestinoNotificacion.DetalleSiniestro("SIN-1"), notificacionId = "N-9")
        )
        compose.waitUntil(timeoutMillis = 5_000) { aperturasConsumidas == 1 }

        compose.onNodeWithText("Siniestro SIN-1").assertIsDisplayed()
        assertEquals(listOf("N-9"), gatewayNotificaciones.leidas)
        assertEquals(1, aperturasConsumidas)
    }

    @Test
    fun unaAperturaSinDestinoPropioAbreLaBandeja() {
        gatewayNotificaciones.bandeja = ResultadoApi.Exito(Bandeja(emptyList(), 0))
        mostrar(AperturaNotificacion(DestinoNotificacion.Bandeja, notificacionId = null))
        compose.waitUntil(timeoutMillis = 5_000) { aperturasConsumidas == 1 }
        compose.waitForIdle()

        compose.onNodeWithText("Aún no tienes notificaciones").assertIsDisplayed()
    }

    @Test
    fun elInterruptorDelPerfilGuardaLaPreferencia() {
        mostrar()
        compose.boton("Perfil").performClick()
        compose.waitForIdle()

        compose.boton("Notificaciones", substring = true).performClick()
        compose.waitForIdle()
        compose.onNodeWithContentDescription("Recibir notificaciones push").performClick()
        compose.waitForIdle()

        assertEquals(listOf(false), gatewayNotificaciones.preferenciasEnviadas)
    }

    @Test
    fun alCerrarSesionSeDaDeBajaElTelefono() {
        mostrar()
        assertTrue(gatewayNotificaciones.bajas.isEmpty())

        compose.boton("Perfil").performClick()
        compose.waitForIdle()
        compose.boton("Cerrar sesión").performClick()
        compose.waitUntil(timeoutMillis = 5_000) { gatewayNotificaciones.bajas.isNotEmpty() }

        assertEquals(listOf("tok-1"), gatewayNotificaciones.bajas)
        assertEquals(1, proveedor.olvidos)
    }
}
