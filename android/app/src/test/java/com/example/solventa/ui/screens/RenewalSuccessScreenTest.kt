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
class RenewalSuccessScreenTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun confirmaLaRenovacionYPermiteVerLaPoliza() {
        val eventos = mutableListOf<String>()
        compose.setContent {
            SolventaTheme {
                RenewalSuccessScreen(
                    onVerPoliza = { eventos += "ver" },
                    onVolver = { eventos += "volver" }
                )
            }
        }

        compose.onNodeWithText("Póliza renovada").assertIsDisplayed()
        compose.onNodeWithText("Actualizamos la vigencia y el documento ya está disponible.")
            .assertIsDisplayed()
        compose.boton("Ver póliza renovada").performClick()

        assertEquals(listOf("ver"), eventos)
    }
}
