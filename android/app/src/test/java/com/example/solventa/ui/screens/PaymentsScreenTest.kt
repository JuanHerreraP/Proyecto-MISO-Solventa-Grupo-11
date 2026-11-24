package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.example.solventa.domain.pagos.ComprobantePago
import com.example.solventa.domain.pagos.ConceptoPago
import com.example.solventa.domain.pagos.EstadoPago
import com.example.solventa.domain.pagos.MetodoPago
import com.example.solventa.domain.pagos.Pago
import com.example.solventa.domain.pagos.PrimaPendiente
import com.example.solventa.domain.pagos.TipoPrimaPendiente
import com.example.solventa.ui.theme.SolventaTheme
import java.math.BigDecimal
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/** HU21: pagos pendientes y comprobante dentro de la pantalla de Pagos. */
@RunWith(RobolectricTestRunner::class)
class PaymentsScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private val eventos = mutableListOf<String>()

    private fun mostrar(
        pagos: List<Pago> = emptyList(),
        pendientes: List<PrimaPendiente> = emptyList(),
        errorPendientes: String? = null,
        comprobanteVisible: Boolean = false,
        comprobante: ComprobantePago? = null,
        errorComprobante: String? = null
    ) {
        compose.setContent {
            SolventaTheme {
                PaymentsScreen(
                    pagos = pagos,
                    cargando = false,
                    error = null,
                    onReintentar = { eventos += "reintentar" },
                    onVolver = {},
                    pendientes = pendientes,
                    errorPendientes = errorPendientes,
                    onPagar = { eventos += "pagar:${it.cotizacionId}" },
                    onFirmar = { eventos += "firmar:${it.cotizacionId}" },
                    onVerComprobante = { eventos += "comprobante:${it.pagoId}" },
                    comprobanteVisible = comprobanteVisible,
                    comprobante = comprobante,
                    errorComprobante = errorComprobante,
                    onCerrarComprobante = { eventos += "cerrar" }
                )
            }
        }
    }

    @Test
    fun permitePagarCotizacionesYRenovacionesPendientes() {
        mostrar(pendientes = listOf(renovacion(), cotizacion()))

        compose.onNodeWithText("Pendientes de pago").assertIsDisplayed()
        compose.onNodeWithText("Renovación — póliza SOL-2026-0001").assertIsDisplayed()
        compose.onNodeWithText("$420.000 COP").assertIsDisplayed()
        compose.onNodeWithText("Microseguro de vida — cotización COT-9").assertIsDisplayed()
        compose.onNodeWithText("$89.000 COP").assertIsDisplayed()
        assertEquals(2, compose.onAllNodesWithText("Fecha límite", substring = true).fetchSemanticsNodes().size)

        compose.onAllNodesWithText("Pagar")[1].performClick()

        assertEquals(listOf("pagar:COT-9"), eventos)
    }

    @Test
    fun lasFirmasPendientesSeCompletanEnLaAppYNoSePagan() {
        mostrar(pendientes = listOf(firmaPendiente()))

        compose.onNodeWithText("Microseguro de vida — contrato por firmar").assertIsDisplayed()
        compose.onNodeWithText("Tu pago fue aprobado. Firma el contrato para emitir la póliza.")
            .assertIsDisplayed()
        compose.onNodeWithText("Pagar").assertDoesNotExist()
        compose.onNodeWithText("Firmar contrato").performClick()
        assertEquals(listOf("firmar:COT-F"), eventos)
    }

    @Test
    fun conPendientesNoMuestraElEstadoVacio() {
        mostrar(pendientes = listOf(cotizacion()))

        compose.onNodeWithText("Todavía no tienes pagos").assertDoesNotExist()
    }

    @Test
    fun sinPagosNiPendientesMuestraElEstadoVacio() {
        mostrar()

        compose.onNodeWithText("Todavía no tienes pagos").assertIsDisplayed()
        compose.onNodeWithText("Pendientes de pago").assertDoesNotExist()
    }

    @Test
    fun informaSiNoPudoConsultarLosPendientes() {
        mostrar(
            pagos = listOf(pago("PAG-1", EstadoPago.APROBADO)),
            errorPendientes = "No pudimos consultar tus pagos pendientes. Inténtalo de nuevo."
        )

        compose.onNodeWithText("No pudimos consultar tus pagos pendientes.", substring = true)
            .assertIsDisplayed()
    }

    @Test
    fun soloLosPagosAprobadosOfrecenElComprobante() {
        mostrar(
            pagos = listOf(
                pago("PAG-1", EstadoPago.APROBADO),
                pago("PAG-2", EstadoPago.RECHAZADO)
            )
        )

        assertEquals(1, compose.onAllNodesWithText("Ver comprobante").fetchSemanticsNodes().size)
        compose.onNodeWithText("Ver comprobante").performClick()

        assertEquals(listOf("comprobante:PAG-1"), eventos)
    }

    @Test
    fun distingueEnElHistorialUnaRenovacionDeUnaCompra() {
        mostrar(
            pagos = listOf(
                pago("PAG-1", EstadoPago.APROBADO, concepto = ConceptoPago.RENOVACION, cotizacion = "COT-REN"),
                pago("PAG-2", EstadoPago.APROBADO, cotizacion = "COT-1")
            )
        )

        compose.onNodeWithText("Renovación — cotización COT-REN").assertIsDisplayed()
        compose.onNodeWithText("Prima — cotización COT-1").assertIsDisplayed()
    }

    @Test
    fun muestraElComprobanteEnUnDialogoYSePuedeCerrar() {
        mostrar(
            pagos = listOf(pago("PAG-1", EstadoPago.APROBADO)),
            comprobanteVisible = true,
            comprobante = comprobante()
        )

        compose.onNodeWithText("Comprobante de pago").assertIsDisplayed()
        compose.onNodeWithText("CP-20261210-ABCD1234").assertIsDisplayed()
        compose.onNodeWithText("Prima de Seguro de viaje").assertIsDisplayed()
        compose.onNodeWithText("$45.000 COP").assertIsDisplayed()
        compose.onNodeWithText("Tarjeta").assertIsDisplayed()
        compose.onNodeWithText("PSP-1").assertIsDisplayed()

        compose.onNodeWithText("Cerrar").performClick()

        assertEquals(listOf("cerrar"), eventos)
    }

    @Test
    fun mientrasSeConsultaElComprobanteMuestraElProgreso() {
        mostrar(pagos = listOf(pago("PAG-1", EstadoPago.APROBADO)), comprobanteVisible = true)

        compose.onNodeWithContentDescription("Cargando el comprobante").assertIsDisplayed()
    }

    @Test
    fun siFallaElComprobanteMuestraElError() {
        mostrar(
            pagos = listOf(pago("PAG-1", EstadoPago.APROBADO)),
            comprobanteVisible = true,
            errorComprobante = "No pudimos consultar el comprobante. Inténtalo de nuevo."
        )

        compose.onNodeWithText("No pudimos consultar el comprobante. Inténtalo de nuevo.")
            .assertIsDisplayed()
    }

    private fun pago(
        id: String,
        estado: EstadoPago,
        concepto: ConceptoPago = ConceptoPago.COMPRA,
        cotizacion: String = "COT-1"
    ) = Pago(
        pagoId = id,
        cotizacionId = cotizacion,
        metodo = MetodoPago.TARJETA,
        monto = BigDecimal("45000.00"),
        moneda = "COP",
        estado = estado,
        concepto = concepto
    )

    private fun renovacion() = PrimaPendiente(
        tipo = TipoPrimaPendiente.RENOVACION,
        referenciaId = "REN-1",
        cotizacionId = "COT-R",
        polizaId = "POL-1",
        numeroPoliza = "SOL-2026-0001",
        nombreRamo = "Microseguro de vida",
        monto = BigDecimal("420000.00"),
        moneda = "COP",
        fechaLimite = "2026-12-31T23:59:59-05:00",
        mensaje = null
    )

    private fun cotizacion() = PrimaPendiente(
        tipo = TipoPrimaPendiente.COTIZACION,
        referenciaId = "COT-9",
        cotizacionId = "COT-9",
        polizaId = null,
        numeroPoliza = null,
        nombreRamo = "Microseguro de vida",
        monto = BigDecimal("89000.00"),
        moneda = "COP",
        fechaLimite = "2026-12-17T15:00:00Z",
        mensaje = null
    )

    private fun firmaPendiente() = PrimaPendiente(
        tipo = TipoPrimaPendiente.FIRMA_PENDIENTE,
        referenciaId = "COT-F",
        cotizacionId = "COT-F",
        polizaId = null,
        numeroPoliza = null,
        nombreRamo = "Microseguro de vida",
        monto = BigDecimal("89000.00"),
        moneda = "COP",
        fechaLimite = null,
        mensaje = "Firma tu contrato en el portal web para emitir tu póliza."
    )

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
