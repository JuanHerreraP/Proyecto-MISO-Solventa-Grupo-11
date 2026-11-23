package com.example.solventa.e2e.pagos

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.solventa.E2ETestActivity
import com.example.solventa.domain.pagos.MetodoPago
import com.example.solventa.domain.pagos.SolicitudPago
import com.example.solventa.ui.screens.PaymentScreen
import com.example.solventa.ui.theme.SolventaTheme
import java.math.BigDecimal
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PagoTarjetaE2ETest {
    @get:Rule val compose = createAndroidComposeRule<E2ETestActivity>()

    @Test
    fun tarjetaRechazadaPermiteReintentarConLaMismaSolicitud() {
        var intentos by mutableIntStateOf(0)
        var solicitud: SolicitudPago? = null

        compose.setContent {
            SolventaTheme {
                PaymentScreen(
                    cotizacionId = "COT-E2E-PAGO",
                    monto = BigDecimal("84000"),
                    moneda = "COP",
                    procesando = false,
                    error = if (intentos == 1) "El pago fue rechazado. Inténtalo de nuevo." else null,
                    onVolver = {},
                    onPagar = { solicitud = it; intentos++ }
                )
            }
        }

        compose.campo("NÚMERO DE TARJETA").performTextInput("4111111111111111")
        compose.campo("VENCIMIENTO").performTextInput("1228")
        compose.campo("CVV").performTextInput("123")
        compose.boton("Pagar prima").performClick()

        compose.onNodeWithText("El pago fue rechazado. Inténtalo de nuevo.").assertIsDisplayed()
        compose.boton("Pagar prima").performClick()

        assertEquals(2, intentos)
        assertEquals(MetodoPago.TARJETA, solicitud?.metodo)
        assertEquals("COT-E2E-PAGO", solicitud?.cotizacionId)
    }
}

private fun androidx.compose.ui.test.SemanticsNodeInteractionsProvider.boton(texto: String) =
    onNode(hasText(texto) and hasClickAction())

private fun androidx.compose.ui.test.SemanticsNodeInteractionsProvider.campo(etiqueta: String) =
    onNode(hasSetTextAction() and hasText(etiqueta))
