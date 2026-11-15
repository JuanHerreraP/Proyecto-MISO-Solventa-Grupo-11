package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.example.solventa.domain.polizas.BloqueoCancelacion
import com.example.solventa.domain.polizas.PropuestaCancelacion
import com.example.solventa.domain.polizas.propuestaCancelacion
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class CancelScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private val eventos = mutableListOf<String>()

    private fun mostrar(
        propuesta: PropuestaCancelacion?,
        cargando: Boolean = false,
        error: String? = null,
        cancelando: Boolean = false
    ) {
        compose.setContent {
            SolventaTheme {
                CancelScreen(
                    propuesta = propuesta,
                    cargando = cargando,
                    error = error,
                    cancelando = cancelando,
                    onConfirmar = { eventos += "confirmar:$it" },
                    onReintentar = { eventos += "reintentar" },
                    onConservar = { eventos += "conservar" },
                    onVolver = { eventos += "volver" }
                )
            }
        }
    }

    @Test
    fun muestraLasConsecuenciasElMotivoYElSaldo() {
        mostrar(propuestaCancelacion())

        compose.onNodeWithText("Confirma tu decisión").assertIsDisplayed()
        compose.onNodeWithText("Perderás la protección asociada a la póliza SOL-VJ-0001.")
            .assertIsDisplayed()
        compose.onNodeWithText("Motivo de cancelación").assertIsDisplayed()
        compose.onNodeWithText("Ya no la necesito").assertIsDisplayed()
        compose.onNodeWithText("Saldo estimado a favor").assertIsDisplayed()
        compose.onNodeWithText("$24.500 COP").assertIsDisplayed()
    }

    @Test
    fun confirmarEnviaElMotivoElegido() {
        mostrar(propuestaCancelacion())

        compose.onNodeWithText("Ya no la necesito").performClick()
        compose.onNodeWithText("El precio es muy alto").performClick()
        compose.boton("Confirmar cancelación").performClick()

        assertEquals(listOf("confirmar:PRECIO_ALTO"), eventos)
    }

    @Test
    fun conservarMiPolizaNoCancelaNada() {
        mostrar(propuestaCancelacion())

        compose.boton("Conservar mi póliza").performClick()

        assertEquals(listOf("conservar"), eventos)
    }

    @Test
    fun siNoSePuedeCancelarExplicaElMotivoYNoOfreceConfirmar() {
        mostrar(
            propuestaCancelacion(
                cancelable = false,
                bloqueos = listOf(
                    BloqueoCancelacion("SINIESTRO_EN_TRAMITE", "Tienes un siniestro en trámite.")
                )
            )
        )

        compose.onNodeWithText("Tienes un siniestro en trámite.").assertIsDisplayed()
        compose.onNodeWithText("Confirmar cancelación").assertDoesNotExist()
        compose.boton("Conservar mi póliza").assertIsDisplayed()
    }

    @Test
    fun mientrasCancelaMuestraElProgreso() {
        mostrar(propuestaCancelacion(), cancelando = true)

        compose.onNodeWithContentDescription("Cancelando la póliza").assertIsDisplayed()
    }

    @Test
    fun mientrasCargaMuestraElProgreso() {
        mostrar(propuesta = null, cargando = true)

        compose.onNodeWithContentDescription("Cargando las condiciones de la cancelación")
            .assertIsDisplayed()
    }

    @Test
    fun conErrorPermiteReintentar() {
        mostrar(propuesta = null, error = "No pudimos consultar la cancelación.")

        compose.boton("Reintentar").performClick()

        assertEquals(listOf("reintentar"), eventos)
    }
}
