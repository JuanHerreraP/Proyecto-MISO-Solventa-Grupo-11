package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.example.solventa.domain.polizas.Billetera
import com.example.solventa.domain.polizas.EstadoPoliza
import com.example.solventa.domain.polizas.billeteraDe
import com.example.solventa.domain.polizas.resumen
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class WalletScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private val eventos = mutableListOf<String>()

    private fun mostrar(billetera: Billetera?, cargando: Boolean = false, error: String? = null) {
        compose.setContent {
            SolventaTheme {
                WalletScreen(
                    billetera = billetera,
                    cargando = cargando,
                    error = error,
                    onVerPoliza = { eventos += "ver:$it" },
                    onReintentar = { eventos += "reintentar" },
                    onVolver = { eventos += "volver" }
                )
            }
        }
    }

    @Test
    fun muestraNumeroRamoEstadoYVigenciaDeCadaPoliza() {
        mostrar(billeteraDe(resumen()))

        compose.onNodeWithText("Vigentes (1)").assertIsDisplayed()
        compose.onNodeWithText("Seguro de viaje").assertIsDisplayed()
        compose.onNodeWithText("Póliza SOL-VJ-0001").assertIsDisplayed()
        compose.onNodeWithText("Vigente").assertIsDisplayed()
        compose.onNodeWithText("1 oct 2026 – 31 dic 2026").assertIsDisplayed()
    }

    @Test
    fun separaLasInactivasYDiceSuEstado() {
        mostrar(
            billeteraDe(
                resumen(id = "A", numero = "SOL-1"),
                resumen(id = "B", numero = "SOL-2", estado = EstadoPoliza.VENCIDA),
                resumen(id = "C", numero = "SOL-3", estado = EstadoPoliza.CANCELADA)
            )
        )

        compose.onNodeWithText("Vigentes (1)").assertIsDisplayed()
        compose.onNodeWithText("Inactivas (2)").assertIsDisplayed()
        compose.onNodeWithText("Vencida").assertIsDisplayed()
        compose.onNodeWithText("Cancelada").assertIsDisplayed()
    }

    @Test
    fun tocarUnaPolizaAbreSuCertificado() {
        mostrar(billeteraDe(resumen(id = "POL-7")))

        compose.boton("Seguro de viaje", substring = true).performClick()

        assertEquals(listOf("ver:POL-7"), eventos)
    }

    @Test
    fun sinPolizasExplicaQueAunNoHay() {
        mostrar(billeteraDe())

        compose.onNodeWithText("Aún no tienes pólizas").assertIsDisplayed()
    }

    @Test
    fun mientrasCargaMuestraElProgreso() {
        mostrar(billetera = null, cargando = true)

        compose.onNodeWithContentDescription("Cargando tus pólizas").assertIsDisplayed()
    }

    @Test
    fun conErrorPermiteReintentarYVolver() {
        mostrar(billetera = null, error = "Sin conexión")

        compose.onNodeWithText("Sin conexión").assertIsDisplayed()
        compose.boton("Reintentar").performClick()
        compose.onNodeWithContentDescription("Volver").performClick()

        assertEquals(listOf("reintentar", "volver"), eventos)
    }

    @Test
    fun unErrorAlRecargarNoOcultaLasPolizasYaCargadas() {
        mostrar(billeteraDe(resumen()), error = "Sin conexión")

        compose.onNodeWithText("Sin conexión").assertIsDisplayed()
        compose.onNodeWithText("Seguro de viaje").assertIsDisplayed()
    }
}
