package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.example.solventa.ui.cotizaciones.CotizacionDemostracion
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class QuotesScreenTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun muestraLaCotizacionYPermiteAbrirSuDetalle() {
        val cotizacion = CotizacionDemostracion.para(RamoCotizacion.VIAJE)
        var seleccionada: String? = null
        compose.setContent {
            SolventaTheme {
                QuotesScreen(
                    cotizaciones = listOf(cotizacion),
                    cargando = false,
                    error = null,
                    onVerCotizacion = { seleccionada = it },
                    onReintentar = {},
                    onVolver = {}
                )
            }
        }

        compose.onNodeWithText("Seguro de viaje").assertIsDisplayed().performClick()

        assertEquals(cotizacion.cotizacionId, seleccionada)
    }

    @Test
    fun muestraElEstadoVacio() {
        compose.setContent {
            SolventaTheme {
                QuotesScreen(emptyList(), false, null, {}, {}, {})
            }
        }

        compose.onNodeWithText("Aún no tienes cotizaciones").assertIsDisplayed()
    }

    @Test
    fun muestraElEstadoDeCarga() {
        compose.setContent {
            SolventaTheme {
                QuotesScreen(emptyList(), true, null, {}, {}, {})
            }
        }

        compose.onNodeWithContentDescription("Cargando tus cotizaciones").assertIsDisplayed()
    }

    @Test
    fun conErrorPermiteReintentar() {
        var reintentos = 0
        compose.setContent {
            SolventaTheme {
                QuotesScreen(
                    cotizaciones = emptyList(),
                    cargando = false,
                    error = "Sin conexión",
                    onVerCotizacion = {},
                    onReintentar = { reintentos++ },
                    onVolver = {}
                )
            }
        }

        compose.onNodeWithText("Sin conexión").assertIsDisplayed()
        compose.boton("Reintentar").performClick()
        assertEquals(1, reintentos)
    }
}
