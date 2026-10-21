package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import com.example.solventa.domain.cotizaciones.CatalogoCotizaciones
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class QuoteFormScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private val calculados = mutableListOf<Map<String, String>>()

    private fun mostrar(ramo: RamoCotizacion) {
        compose.setContent {
            SolventaTheme {
                QuoteFormScreen(
                    definicion = CatalogoCotizaciones.definicion(ramo),
                    onVolver = {},
                    onCalcular = { calculados += it }
                )
            }
        }
    }

    @Test
    fun viajeMuestraTodosSusCamposEnUnaColumna() {
        mostrar(RamoCotizacion.VIAJE)

        compose.onNodeWithText("Datos de tu viaje").assertIsDisplayed()
        compose.onNodeWithText("DESTINO").assertIsDisplayed()
        compose.onNodeWithText("FECHA DE SALIDA").assertIsDisplayed()
        compose.onNodeWithText("FECHA DE REGRESO").assertIsDisplayed()
        compose.onNodeWithText("NÚMERO DE VIAJEROS").assertIsDisplayed()
        compose.onNodeWithText("VALOR ASEGURADO").assertIsDisplayed()
    }

    @Test
    fun cadaRamoUsaSuDefinicionDeCampos() {
        mostrar(RamoCotizacion.DISPOSITIVOS)
        compose.onNodeWithText("Datos de tu dispositivo").assertIsDisplayed()
        compose.onNodeWithText("TIPO DE DISPOSITIVO").assertIsDisplayed()
        compose.onNodeWithText("MARCA").assertIsDisplayed()
        compose.onNodeWithText("MODELO").assertIsDisplayed()
    }

    @Test
    fun informaLosCamposObligatoriosAntesDeCalcular() {
        mostrar(RamoCotizacion.VIAJE)

        compose.boton("Calcular cotización").performScrollTo().performClick()

        compose.onAllNodesWithText("Este campo es obligatorio.").assertCountEquals(5)
        assertEquals(emptyList<Map<String, String>>(), calculados)
    }

    @Test
    fun parametricoSoloMuestraElDatoCondicionalDelEventoElegido() {
        mostrar(RamoCotizacion.PARAMETRICO)

        compose.onNodeWithText("NÚMERO DE VUELO").assertDoesNotExist()
        compose.onNodeWithText("UBICACIÓN").assertDoesNotExist()
        compose.onNodeWithTag("campo_tipo_evento").performClick()
        compose.waitForIdle()
        compose.onNodeWithTag("opcion_tipo_evento_RETRASO_VUELO").performClick()

        compose.onNodeWithText("NÚMERO DE VUELO").assertIsDisplayed()
        compose.onNodeWithText("UBICACIÓN").assertDoesNotExist()
    }
}
