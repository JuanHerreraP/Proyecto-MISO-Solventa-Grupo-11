package com.example.solventa.ui.accesibilidad

import androidx.compose.runtime.Composable
import androidx.compose.ui.semantics.SemanticsNode
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.semantics.getOrNull
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.dp
import androidx.test.core.app.ApplicationProvider
import com.example.solventa.R
import com.example.solventa.domain.auth.Perfil
import com.example.solventa.domain.pagos.ConceptoPago
import com.example.solventa.domain.pagos.EstadoPago
import com.example.solventa.domain.pagos.MetodoPago
import com.example.solventa.domain.pagos.Pago
import com.example.solventa.domain.polizas.EstadoPoliza
import com.example.solventa.domain.polizas.MovimientoReciente
import com.example.solventa.domain.polizas.billeteraDe
import com.example.solventa.domain.polizas.historialPoliza
import com.example.solventa.domain.polizas.resumen
import com.example.solventa.i18n.Idioma
import com.example.solventa.i18n.tr
import com.example.solventa.ui.screens.BiometricalLoginScreen
import com.example.solventa.ui.screens.CredentialsLoginScreen
import com.example.solventa.ui.screens.HomeScreen
import com.example.solventa.ui.screens.PaymentsScreen
import com.example.solventa.ui.screens.ProfileScreen
import com.example.solventa.ui.screens.RegisterScreen
import com.example.solventa.ui.screens.WalletScreen
import com.example.solventa.ui.screens.WelcomeScreen
import com.example.solventa.ui.theme.SolventaTheme
import java.math.BigDecimal
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.ParameterizedRobolectricTestRunner

/**
 * Accesibilidad de las pantallas principales, en español e inglés (guías de Android y WCAG 2.1):
 * - todo elemento táctil tiene un nombre que el lector de pantalla (TalkBack) puede anunciar;
 * - todo campo de texto tiene una etiqueta;
 * - los elementos táctiles miden al menos 40 dp (los componentes de Material amplían su área de
 *   toque a 48 dp con minimumInteractiveComponentSize).
 */
@RunWith(ParameterizedRobolectricTestRunner::class)
class AccesibilidadTest(private val opcion: Idioma.Opcion) {

    companion object {
        @JvmStatic
        @ParameterizedRobolectricTestRunner.Parameters(name = "{0}")
        fun idiomas() = listOf(arrayOf<Any>(Idioma.Opcion.ESPANOL), arrayOf<Any>(Idioma.Opcion.INGLES))
    }

    @get:Rule
    val compose = createComposeRule()

    private val perfil = Perfil(
        "u-1", "María", "Torres", "maria.torres@correo.com", "CLIENTE",
        "CC", "1020456789", "3001234567"
    )

    private fun mostrar(contenido: @Composable () -> Unit) {
        Idioma.establecer(ApplicationProvider.getApplicationContext(), opcion)
        compose.setContent { SolventaTheme { contenido() } }
        compose.waitForIdle()
    }

    private fun nombre(nodo: SemanticsNode): String {
        val c = nodo.config
        return listOfNotNull(
            c.getOrNull(SemanticsProperties.ContentDescription)?.joinToString(" "),
            c.getOrNull(SemanticsProperties.Text)?.joinToString(" ") { it.text },
            c.getOrNull(SemanticsProperties.EditableText)?.text
        ).joinToString(" ").trim()
    }

    private fun revisar(pantalla: String) {
        val problemas = mutableListOf<String>()
        val densidad = compose.density

        compose.onAllNodes(hasClickAction()).fetchSemanticsNodes().forEach { nodo ->
            // Tamaño real del elemento, aunque esté fuera de la parte visible de una pantalla con scroll
            // (boundsInRoot lo recorta y daría 0×0).
            val ancho = with(densidad) { nodo.size.width.toDp() }
            val alto = with(densidad) { nodo.size.height.toDp() }
            if (nombre(nodo).isBlank()) {
                problemas += "$pantalla: elemento táctil sin nombre accesible en ${nodo.positionInRoot}"
            }
            if (ancho < 40.dp || alto < 40.dp) {
                problemas += "$pantalla: '${nombre(nodo)}' mide ${ancho.value.toInt()}×${alto.value.toInt()} dp"
            }
        }
        compose.onAllNodes(hasSetTextAction()).fetchSemanticsNodes().forEach { campo ->
            val etiqueta = listOfNotNull(
                campo.config.getOrNull(SemanticsProperties.ContentDescription)?.joinToString(" "),
                campo.config.getOrNull(SemanticsProperties.Text)?.joinToString(" ") { it.text }
            ).joinToString(" ").trim()
            if (etiqueta.isBlank()) problemas += "$pantalla: campo de texto sin etiqueta en ${campo.boundsInRoot}"
        }
        assertEquals("Problemas de accesibilidad", emptyList<String>(), problemas)
    }

    @Test
    fun bienvenida() {
        mostrar { WelcomeScreen(onLoginClick = {}, onRegisterClick = {}) }
        revisar("Bienvenida")
    }

    @Test
    fun ingresoBiometrico() {
        mostrar {
            BiometricalLoginScreen(
                onBackClick = {}, onBiometricClick = {}, onUseCredentialsClick = {}, onRegisterClick = {},
                biometriaDisponible = true, cargando = false, mensaje = null
            )
        }
        revisar("Ingreso biométrico")
    }

    @Test
    fun ingresoConCredenciales() {
        mostrar {
            CredentialsLoginScreen(
                onBackClick = {}, onLoginSubmit = { _, _ -> }, onSwitchToBiometric = {},
                onForgotPasswordClick = {}, cargando = false, mensaje = null
            )
        }
        revisar("Ingreso con credenciales")
    }

    @Test
    fun registro() {
        mostrar { RegisterScreen(onBackClick = {}, onRegisterSubmit = {}, onLoginClick = {}, cargando = false, mensaje = null) }
        revisar("Registro")
    }

    @Test
    fun inicio() {
        val movimientos = historialPoliza("POL-1").movimientos.map { MovimientoReciente(it, "Seguro de viaje") }
        mostrar {
            HomeScreen(
                perfil = perfil,
                biometriaActivada = true,
                biometriaDisponible = true,
                ofrecerActivarBiometria = false,
                mensaje = null,
                cerrandoSesion = false,
                onActivarBiometria = {},
                onSolicitarActivacion = {},
                onDescartarActivacion = {},
                onCerrarSesion = {},
                onVerBilletera = {},
                onVerCotizaciones = {},
                onVerPagos = {},
                onVerSiniestros = {},
                onCotizarSeguro = {},
                cantidadPolizasActivas = 2,
                movimientosRecientes = movimientos,
                notificacionesSinLeer = 2,
                sinConexion = false,
                ultimaSincronizacionMs = System.currentTimeMillis()
            )
        }
        revisar("Inicio")
    }

    @Test
    fun billetera() {
        mostrar {
            WalletScreen(
                billetera = billeteraDe(
                    resumen(id = "A", numero = "SOL-2026-0001"),
                    resumen(id = "B", numero = "SOL-2025-0107", estado = EstadoPoliza.VENCIDA)
                ),
                cargando = false,
                error = null,
                sinConexion = false,
                ultimaSincronizacionMs = System.currentTimeMillis(),
                datosAntiguos = false,
                falloSincronizacionPersistente = false,
                onVerPoliza = {},
                onReintentar = {},
                onVolver = {}
            )
        }
        revisar("Billetera")
    }

    @Test
    fun pagos() {
        val pago = Pago(
            pagoId = "PAG-1", cotizacionId = "COT-1", metodo = MetodoPago.TARJETA,
            monto = BigDecimal("84000.00"), moneda = "COP", estado = EstadoPago.APROBADO,
            concepto = ConceptoPago.COMPRA
        )
        mostrar {
            PaymentsScreen(
                pagos = listOf(pago), cargando = false, error = null, onReintentar = {}, onVolver = {},
                pendientes = emptyList(), errorPendientes = null, onPagar = {}, onVerComprobante = {},
                comprobanteVisible = false, comprobante = null, errorComprobante = null, onCerrarComprobante = {}
            )
        }
        revisar("Pagos")
    }

    private fun perfil() = mostrar {
        ProfileScreen(
            perfil = perfil,
            biometriaActivada = true,
            sinConexion = false,
            cerrandoSesion = false,
            onCerrarSesion = {},
            onInicio = {},
            onPolizas = {},
            onSiniestros = {}
        )
    }

    @Test
    fun perfilYSelectorDeIdioma() {
        perfil()
        revisar("Perfil")
        compose.onNodeWithText(tr(R.string.profile_idioma_y_moneda)).performClick()
        compose.waitForIdle()
        revisar("Idioma y moneda")
        assertTrue(compose.onAllNodes(hasClickAction()).fetchSemanticsNodes().isNotEmpty())
    }
}
