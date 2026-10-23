package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class NewQuoteScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private val seleccionados = mutableListOf<RamoCotizacion>()

    private fun mostrar() {
        compose.setContent {
            SolventaTheme {
                NewQuoteScreen(
                    onVolver = {},
                    onSeleccionarRamo = { seleccionados += it }
                )
            }
        }
    }

    @Test
    fun muestraLosCuatroRamosDisponibles() {
        mostrar()

        compose.onNodeWithText("¿Qué quieres proteger?").assertIsDisplayed()
        compose.onNodeWithText("Viaje").assertIsDisplayed()
        compose.onNodeWithText("Dispositivos").assertIsDisplayed()
        compose.onNodeWithText("Vida").assertIsDisplayed()
        compose.onNodeWithText("Paramétrico").assertIsDisplayed()
    }

    @Test
    fun entregaElRamoSeleccionado() {
        mostrar()

        compose.boton("Dispositivos").performClick()

        assertEquals(listOf(RamoCotizacion.DISPOSITIVOS), seleccionados)
    }
}
