package com.example.solventa.e2e.pagos

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.isToggleable
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.solventa.E2ETestActivity
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.example.solventa.domain.firmas.ContratoFirma
import com.example.solventa.domain.firmas.EstadoFirma
import com.example.solventa.domain.firmas.ProcesoFirma
import com.example.solventa.domain.pagos.EstadoPago
import com.example.solventa.domain.pagos.MetodoPago
import com.example.solventa.domain.pagos.Pago
import com.example.solventa.domain.pagos.SolicitudPago
import com.example.solventa.ui.cotizaciones.CotizacionDemostracion
import com.example.solventa.ui.screens.PaymentResultScreen
import com.example.solventa.ui.screens.PaymentScreen
import com.example.solventa.ui.screens.QuoteResultScreen
import com.example.solventa.ui.screens.QuotesScreen
import com.example.solventa.ui.screens.SignatureScreen
import com.example.solventa.ui.theme.SolventaTheme
import java.math.BigDecimal
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Flujos instrumentados para pagar una cotización guardada y firmar su contrato. */
@RunWith(AndroidJUnit4::class)
class CotizacionYFirmaE2ETest {
    @get:Rule val compose = createAndroidComposeRule<E2ETestActivity>()

    @Test
    fun cotizacionListadaPermiteContinuarHastaElPago() {
        val cotizacion = CotizacionDemostracion.para(RamoCotizacion.VIAJE)
        var paso by mutableStateOf("listado")
        var solicitud: SolicitudPago? = null

        compose.setContent {
            SolventaTheme {
                when (paso) {
                    "listado" -> QuotesScreen(
                        cotizaciones = listOf(cotizacion),
                        cargando = false,
                        error = null,
                        onVerCotizacion = { paso = "detalle" },
                        onReintentar = {},
                        onVolver = {}
                    )
                    "detalle" -> QuoteResultScreen(
                        cotizacion = cotizacion,
                        onVolver = { paso = "listado" },
                        onAceptar = { paso = "pago" },
                        onCrearOtra = {}
                    )
                    else -> PaymentScreen(
                        cotizacionId = cotizacion.cotizacionId,
                        monto = cotizacion.primaTotal,
                        moneda = cotizacion.moneda,
                        procesando = false,
                        error = null,
                        onVolver = { paso = "detalle" },
                        onPagar = { solicitud = it }
                    )
                }
            }
        }

        compose.boton("Seguro de viaje").performClick()
        compose.boton("Aceptar y continuar").performClick()
        compose.onNodeWithText("PAGO DE LA PRIMA").assertIsDisplayed()

        compose.campo("NÚMERO DE TARJETA").performTextInput("4111111111111111")
        compose.campo("VENCIMIENTO").performTextInput("1228")
        compose.campo("CVV").performTextInput("123")
        compose.boton("Pagar prima").performClick()

        assertEquals(cotizacion.cotizacionId, solicitud?.cotizacionId)
        assertEquals(MetodoPago.TARJETA, solicitud?.metodo)
    }

    @Test
    fun firmaElectronicaSolicitaOtpYEmiteLaPoliza() {
        val proceso = procesoFirma()
        var estado by mutableStateOf(EstadoFirma(proceso = proceso))
        var polizaVista: String? = null

        compose.setContent {
            SolventaTheme {
                SignatureScreen(
                    estado = estado,
                    onSolicitarCodigo = {
                        estado = estado.copy(proceso = proceso.copy(otpDestino = "***3692"))
                    },
                    onFirmar = { codigo ->
                        if (codigo == "123456") {
                            estado = estado.copy(proceso = proceso.copy(polizaId = "POL-E2E-FIRMA"))
                        }
                    },
                    onVolver = {},
                    onVerPoliza = { polizaVista = it }
                )
            }
        }

        compose.boton("Enviar código por SMS").performClick()
        compose.onNodeWithText("Código enviado a ***3692").assertIsDisplayed()
        compose.campo("Código de seis dígitos").performTextInput("123456")
        compose.onNode(isToggleable()).performClick()
        compose.boton("Firmar y emitir póliza").performClick()

        compose.onNodeWithText("¡Contrato firmado!").assertIsDisplayed()
        compose.boton("Ver póliza").performClick()
        assertEquals("POL-E2E-FIRMA", polizaVista)
    }
}

private fun procesoFirma() = ProcesoFirma(
    cotizacionId = "COT-E2E-FIRMA",
    estado = "FIRMA_PENDIENTE",
    contrato = ContratoFirma(
        nombreRamo = "Seguro de viaje",
        coberturaPrincipal = "Asistencia integral de viaje",
        sumaAsegurada = BigDecimal("5000000"),
        primaTotal = BigDecimal("148900"),
        moneda = "COP",
        clausulas = listOf("La cobertura opera durante las fechas del viaje."),
        exclusionesPrincipales = listOf("No cubre hechos previos a la vigencia.")
    ),
    huellaDocumento = "e2ehuelladocumento",
    otpDestino = null,
    polizaId = null
)

private fun androidx.compose.ui.test.SemanticsNodeInteractionsProvider.boton(texto: String) =
    onNode(hasText(texto) and hasClickAction())

private fun androidx.compose.ui.test.SemanticsNodeInteractionsProvider.campo(etiqueta: String) =
    onNode(hasSetTextAction() and hasText(etiqueta))
