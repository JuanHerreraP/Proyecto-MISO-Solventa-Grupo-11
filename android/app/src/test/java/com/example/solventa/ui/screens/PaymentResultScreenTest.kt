package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import com.example.solventa.domain.pagos.ComprobantePago
import com.example.solventa.domain.pagos.ConceptoPago
import com.example.solventa.domain.pagos.EstadoPago
import com.example.solventa.domain.pagos.MetodoPago
import com.example.solventa.domain.pagos.Pago
import com.example.solventa.ui.theme.SolventaTheme
import java.math.BigDecimal
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/** HU21: la confirmación del pago muestra el comprobante y el siguiente paso. */
@RunWith(RobolectricTestRunner::class)
class PaymentResultScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private fun mostrar(estado: EstadoPago, comprobante: ComprobantePago? = null) {
        compose.setContent {
            SolventaTheme {
                PaymentResultScreen(
                    pago = Pago(
                        pagoId = "PAG-1",
                        cotizacionId = "COT-1",
                        metodo = MetodoPago.TARJETA,
                        monto = BigDecimal("45000.00"),
                        moneda = "COP",
                        estado = estado
                    ),
                    onReintentar = {},
                    onCerrar = {},
                    comprobante = comprobante
                )
            }
        }
    }

    @Test
    fun elPagoAprobadoMuestraElComprobanteYPideFirmarEnElPortalWeb() {
        mostrar(EstadoPago.APROBADO, comprobante())

        compose.onNodeWithText("¡Pago exitoso!").assertIsDisplayed()
        compose.onNodeWithText("firma tu contrato en el portal web", substring = true)
            .assertIsDisplayed()
        compose.onNodeWithText("Comprobante CP-20261210-ABCD1234").assertIsDisplayed()
        compose.onNodeWithText("Prima de Seguro de viaje").assertIsDisplayed()
    }

    @Test
    fun sinComprobanteLaConfirmacionSigueSiendoValida() {
        mostrar(EstadoPago.APROBADO)

        compose.onNodeWithText("¡Pago exitoso!").assertIsDisplayed()
        compose.onNodeWithText("Comprobante", substring = true).assertDoesNotExist()
    }

    @Test
    fun unPagoRechazadoNoMuestraComprobanteYPermiteReintentar() {
        mostrar(EstadoPago.RECHAZADO, comprobante())

        compose.onNodeWithText("Pago rechazado").assertIsDisplayed()
        compose.onNodeWithText("Reintentar pago").assertIsDisplayed()
        compose.onNodeWithText("Comprobante CP-20261210-ABCD1234").assertDoesNotExist()
    }

    private fun comprobante() = ComprobantePago(
        numero = "CP-20261210-ABCD1234",
        pagoId = "PAG-1",
        concepto = ConceptoPago.COMPRA,
        descripcion = "Prima de Seguro de viaje",
        polizaId = null,
        numeroPoliza = null,
        monto = BigDecimal("45000.00"),
        moneda = "COP",
        metodo = MetodoPago.TARJETA,
        referenciaPasarela = "PSP-1",
        pagadoEn = "2026-12-10T15:00:00Z"
    )
}
