package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.example.solventa.domain.auth.Perfil
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class ProfileScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private val eventos = mutableListOf<String>()

    private fun mostrar() {
        compose.setContent {
            SolventaTheme {
                ProfileScreen(
                    perfil = Perfil(
                        "u-1", "María", "Solano", "maria@correo.com", "CLIENTE",
                        "CC", "1020456789", "3001234567"
                    ),
                    biometriaActivada = true,
                    sinConexion = false,
                    cerrandoSesion = false,
                    onCerrarSesion = { eventos += "cerrar" },
                    onInicio = {},
                    onPolizas = {},
                    onSiniestros = {}
                )
            }
        }
    }

    @Test
    fun muestraLaCuentaAutenticada() {
        mostrar()

        compose.onNodeWithText("Cliente").assertIsDisplayed()
        compose.onNodeWithText("María Solano").assertIsDisplayed()
        compose.onNodeWithText("maria@correo.com").assertIsDisplayed()
    }

    @Test
    fun muestraDocumentoYTelefonoEnElDetalle() {
        mostrar()

        compose.boton("Datos personales").performClick()
        compose.onNodeWithText("CC 1020456789").assertIsDisplayed()
        compose.onNodeWithText("3001234567").assertIsDisplayed()
    }

    @Test
    fun permiteCerrarSesionDesdePerfil() {
        mostrar()

        compose.boton("Cerrar sesión").performClick()
        assertEquals(listOf("cerrar"), eventos)
    }
}
