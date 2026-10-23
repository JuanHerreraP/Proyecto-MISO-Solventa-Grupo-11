package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.example.solventa.ui.cotizaciones.CotizacionDemostracion
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class QuoteResultScreenTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun muestraPrimaCoberturaYVigenciaRecibidas() {
        compose.setContent {
            SolventaTheme {
                QuoteResultScreen(
                    cotizacion = CotizacionDemostracion.para(RamoCotizacion.VIAJE),
                    onVolver = {},
                    onAceptar = {},
                    onCrearOtra = {}
                )
            }
        }

        compose.onNodeWithText("Protección para tu viaje").assertIsDisplayed()
        compose.onNodeWithText("$148.900 COP").assertIsDisplayed()
        compose.onNodeWithText("VIGENTE 24 H").assertIsDisplayed()
        compose.onNodeWithText("Asistencia integral de viaje").assertIsDisplayed()
        compose.onNodeWithText("Suma asegurada: $5.000.000 COP").assertIsDisplayed()
    }

    @Test
    fun ejecutaLasAccionesSinAcoplarseAlSiguienteFlujo() {
        var aceptaciones = 0
        var nuevas = 0
        compose.setContent {
            SolventaTheme {
                QuoteResultScreen(
                    cotizacion = CotizacionDemostracion.para(RamoCotizacion.VIDA),
                    onVolver = {},
                    onAceptar = { aceptaciones++ },
                    onCrearOtra = { nuevas++ }
                )
            }
        }

        compose.onNodeWithText("Aceptar y continuar").performScrollTo().performClick()
        compose.onNodeWithText("Crear otra cotización").performScrollTo().performClick()

        assertEquals(1, aceptaciones)
        assertEquals(1, nuevas)
    }

    @Test
    fun soloInformaPersonalizacionCuandoExistePerfil() {
        val cotizacion = CotizacionDemostracion.para(RamoCotizacion.DISPOSITIVOS)
            .copy(perfilRiesgoId = null)
        compose.setContent {
            SolventaTheme {
                QuoteResultScreen(
                    cotizacion = cotizacion,
                    onVolver = {},
                    onAceptar = {},
                    onCrearOtra = {}
                )
            }
        }

        compose.onNodeWithText("Precio personalizado con la información que autorizaste.")
            .assertDoesNotExist()
    }
}

