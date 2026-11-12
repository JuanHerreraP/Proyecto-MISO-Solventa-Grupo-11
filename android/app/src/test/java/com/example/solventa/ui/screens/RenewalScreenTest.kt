package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.example.solventa.domain.polizas.BloqueoRenovacion
import com.example.solventa.domain.polizas.PropuestaRenovacion
import com.example.solventa.domain.polizas.propuestaRenovacion
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class RenewalScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private val eventos = mutableListOf<String>()

    private fun mostrar(
        propuesta: PropuestaRenovacion?,
        cargando: Boolean = false,
        error: String? = null,
        iniciando: Boolean = false
    ) {
        compose.setContent {
            SolventaTheme {
                RenewalScreen(
                    propuesta = propuesta,
                    cargando = cargando,
                    error = error,
                    iniciando = iniciando,
                    onConfirmar = { eventos += "confirmar" },
                    onReintentar = { eventos += "reintentar" },
                    onAhoraNo = { eventos += "ahora-no" },
                    onVolver = { eventos += "volver" }
                )
            }
        }
    }

    @Test
    fun muestraLaNuevaVigenciaLasCoberturasYLaPrima() {
        mostrar(propuestaRenovacion())

        compose.onNodeWithText("Continúa protegido").assertIsDisplayed()
        compose.onNodeWithText("Nueva vigencia").assertIsDisplayed()
        compose.onNodeWithText("1 ene 2027 – 31 dic 2027").assertIsDisplayed()
        compose.onNodeWithText("Asistencia médica").assertIsDisplayed()
        compose.onNodeWithText("Prima de renovación").assertIsDisplayed()
        compose.onNodeWithText("$164.700 COP").assertIsDisplayed()
    }

    @Test
    fun confirmarYAhoraNoAvisanALaPantalla() {
        mostrar(propuestaRenovacion())

        compose.boton("Confirmar y pagar").performClick()
        compose.boton("Ahora no").performClick()

        assertEquals(listOf("confirmar", "ahora-no"), eventos)
    }

    @Test
    fun siNoSePuedeRenovarExplicaElMotivoYNoOfreceElPago() {
        mostrar(
            propuestaRenovacion(
                renovable = false,
                bloqueos = listOf(BloqueoRenovacion("FUERA_DE_VENTANA", "Podrás renovar desde el 01/12/2026."))
            )
        )

        compose.onNodeWithText("Podrás renovar desde el 01/12/2026.").assertIsDisplayed()
        compose.onNodeWithText("Confirmar y pagar").assertDoesNotExist()
        compose.boton("Ahora no").assertIsDisplayed()
    }

    @Test
    fun mientrasCargaMuestraElProgreso() {
        mostrar(propuesta = null, cargando = true)

        compose.onNodeWithContentDescription("Cargando las condiciones de la renovación")
            .assertIsDisplayed()
    }

    @Test
    fun conErrorPermiteReintentar() {
        mostrar(propuesta = null, error = "No pudimos consultar la renovación.")

        compose.onNodeWithText("No pudimos consultar la renovación.").assertIsDisplayed()
        compose.boton("Reintentar").performClick()

        assertEquals(listOf("reintentar"), eventos)
    }

    @Test
    fun muestraElErrorAlConfirmar() {
        mostrar(propuestaRenovacion(), error = "No pudimos iniciar la renovación. Inténtalo de nuevo.")

        compose.onNodeWithText("No pudimos iniciar la renovación. Inténtalo de nuevo.").assertIsDisplayed()
    }
}
