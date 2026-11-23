package com.example.solventa.e2e.asesores

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.solventa.E2ETestActivity
import com.example.solventa.domain.asesor.ClienteDeAsesor
import com.example.solventa.ui.screens.AdvisorHomeScreen
import com.example.solventa.ui.screens.ClaimFormScreen
import com.example.solventa.ui.screens.PolizaElegible
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class FlujosAsesorE2ETest {
    @get:Rule val compose = createAndroidComposeRule<E2ETestActivity>()

    @Test
    fun asesorAbreElReporteAsistidoSoloParaUnClienteAsociado() {
        val cliente = ClienteDeAsesor("CLI-E2E-AS", "Ana", "Pérez", "ana@solventa.co")
        var seleccionado: ClienteDeAsesor? by mutableStateOf(null)

        compose.setContent {
            SolventaTheme {
                if (seleccionado == null) {
                    AdvisorHomeScreen(
                        nombre = "Andrea",
                        clientes = listOf(cliente),
                        cargando = false,
                        error = null,
                        asociando = false,
                        errorAsociar = null,
                        avisoAsociado = null,
                        cerrandoSesion = false,
                        onAsociarCliente = {},
                        onRegistrarSiniestro = { seleccionado = it },
                        onCerrarSesion = {}
                    )
                } else {
                    ClaimFormScreen(
                        polizas = listOf(PolizaElegible("POL-E2E-AS", "Seguro de viaje")),
                        registrando = false,
                        error = null,
                        clienteNombre = seleccionado?.nombreCompleto,
                        onRegistrar = { _, _, _, _, _, _, _ -> },
                        onVolver = {}
                    )
                }
            }
        }

        compose.boton("Ana Pérez").performClick()

        compose.onNodeWithText("CLIENTE").assertIsDisplayed()
        compose.onNodeWithText("Ana Pérez").assertIsDisplayed()
        compose.onNodeWithText("Reportar siniestro").assertIsDisplayed()
    }

    @Test
    fun asesorSinPolizaElegibleNoPuedeRegistrarElSiniestro() {
        var registros = 0
        compose.setContent {
            SolventaTheme {
                ClaimFormScreen(
                    polizas = emptyList(),
                    registrando = false,
                    error = null,
                    clienteNombre = "Cliente sin asociación",
                    onRegistrar = { _, _, _, _, _, _, _ -> registros++ },
                    onVolver = {}
                )
            }
        }

        compose.onNodeWithText("El cliente no tiene pólizas vigentes para reportar un siniestro.")
            .assertIsDisplayed()
        compose.boton("Registrar siniestro").performClick()

        assertEquals(0, registros)
    }
}

private fun androidx.compose.ui.test.SemanticsNodeInteractionsProvider.boton(texto: String) =
    onNode(hasText(texto) and hasClickAction())
