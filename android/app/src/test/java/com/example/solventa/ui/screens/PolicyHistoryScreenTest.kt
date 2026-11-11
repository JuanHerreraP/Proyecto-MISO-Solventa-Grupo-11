package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import com.example.solventa.domain.polizas.HistorialPoliza
import com.example.solventa.domain.polizas.historialPoliza
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class PolicyHistoryScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private val eventos = mutableListOf<String>()

    private fun mostrar(
        historial: HistorialPoliza? = historialPoliza(),
        cargando: Boolean = false,
        error: String? = null,
        numeroPoliza: String = "SOL-VJ-0001",
        nombreRamo: String = "Seguro de viaje"
    ) {
        compose.setContent {
            SolventaTheme {
                PolicyHistoryScreen(
                    numeroPoliza = numeroPoliza,
                    nombreRamo = nombreRamo,
                    historial = historial,
                    cargando = cargando,
                    error = error,
                    onReintentar = { eventos += "reintentar" },
                    onVolver = { eventos += "volver" }
                )
            }
        }
    }

    @Test
    fun muestraLosMovimientosDeLaPoliza() {
        mostrar()

        compose.onNodeWithText("Seguro de viaje").assertIsDisplayed()
        compose.onNodeWithText("Póliza SOL-VJ-0001").assertIsDisplayed()
        compose.onNodeWithText("Emisión de póliza").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Pago de prima inicial").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Modificación contractual").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Aumenta la suma asegurada").performScrollTo().assertIsDisplayed()
    }

    @Test
    fun muestraElEstadoVacio() {
        mostrar(
            historial = HistorialPoliza(
                polizaId = "POL-1",
                numeroPoliza = "SOL-VJ-0001",
                nombreRamo = "Seguro de viaje",
                estado = "VIGENTE",
                movimientos = emptyList()
            )
        )

        compose.onNodeWithText("Esta póliza no tiene movimientos registrados.")
            .performScrollTo()
            .assertIsDisplayed()
    }

    @Test
    fun mientrasCargaMuestraElProgreso() {
        mostrar(historial = null, cargando = true)

        compose.onNodeWithContentDescription("Cargando movimientos").assertIsDisplayed()
    }

    @Test
    fun conErrorPermiteReintentar() {
        mostrar(historial = null, error = "No pudimos cargar el historial.")

        compose.onNodeWithText("No pudimos cargar el historial.").assertIsDisplayed()
        compose.boton("Reintentar").performClick()

        assertEquals(listOf("reintentar"), eventos)
    }
}
