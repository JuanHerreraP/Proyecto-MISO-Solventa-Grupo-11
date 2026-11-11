package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class CancelSuccessScreenTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun confirmaLaCancelacionYVuelveALasPolizas() {
        val eventos = mutableListOf<String>()
        compose.setContent {
            SolventaTheme {
                CancelSuccessScreen(onVolverALasPolizas = { eventos += "polizas" }, onVolver = {})
            }
        }

        compose.onNodeWithText("Póliza cancelada").assertIsDisplayed()
        compose.boton("Volver a mis pólizas").performClick()

        assertEquals(listOf("polizas"), eventos)
    }
}
