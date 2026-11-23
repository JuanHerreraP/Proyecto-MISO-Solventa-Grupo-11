package com.example.solventa.e2e.siniestros

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.solventa.E2ETestActivity
import com.example.solventa.domain.siniestros.BorradorSiniestro
import com.example.solventa.domain.siniestros.EvidenciaLocal
import com.example.solventa.domain.siniestros.EstadoSiniestro
import com.example.solventa.domain.siniestros.OrigenSiniestro
import com.example.solventa.domain.siniestros.Siniestro
import com.example.solventa.domain.siniestros.Siniestros
import com.example.solventa.domain.siniestros.TipoEvidencia
import com.example.solventa.domain.siniestros.TipoSiniestro
import com.example.solventa.ui.siniestros.AccionesEvidencia
import com.example.solventa.ui.screens.ClaimFormScreen
import com.example.solventa.ui.screens.ClaimsScreen
import com.example.solventa.ui.screens.PolizaElegible
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ReporteSiniestroE2ETest {
    @get:Rule val compose = createAndroidComposeRule<E2ETestActivity>()

    @Test
    fun reporteConEvidenciaGuardadaApareceEnElListado() {
        var registrado by mutableStateOf(false)

        compose.setContent {
            SolventaTheme {
                if (registrado) {
                    ClaimsScreen(
                        siniestros = Siniestros(listOf(siniestroRegistrado())),
                        cargando = false,
                        error = null,
                        onReintentar = {},
                        onVolver = {}
                    )
                } else {
                    ClaimFormScreen(
                        polizas = listOf(PolizaElegible("POL-E2E-SIN", "Seguro de viaje")),
                        registrando = false,
                        error = null,
                        borrador = borradorConEvidencia(),
                        acciones = AccionesEvidencia({}, {}, {}),
                        onRegistrar = { _, _, _, _, _, _, _ -> registrado = true },
                        onVolver = {}
                    )
                }
            }
        }

        compose.onNodeWithText("EVIDENCIAS (1/10)").performScrollTo().assertIsDisplayed()
        compose.boton("Registrar siniestro").performScrollTo().performClick()

        compose.onNodeWithText("Mis siniestros").assertIsDisplayed()
        compose.onNodeWithText("Póliza POL-E2E-SIN").assertIsDisplayed()
    }
}

private fun androidx.compose.ui.test.SemanticsNodeInteractionsProvider.boton(texto: String) =
    onNode(hasText(texto) and hasClickAction())

private fun borradorConEvidencia() = BorradorSiniestro(
    id = "borrador-e2e",
    polizaId = "POL-E2E-SIN",
    tipoSiniestro = TipoSiniestro.ROBO_HURTO,
    fechaEvento = "2026-11-15",
    horaEvento = "10:30",
    lugar = "Bogotá",
    descripcion = "Daño cubierto durante el viaje.",
    estimacionDanos = "250000",
    evidencias = listOf(
        EvidenciaLocal(
            id = "evi-e2e",
            rutaArchivo = "/private/evidencia.jpg",
            tipoContenido = "image/jpeg",
            tipo = TipoEvidencia.FOTO,
            tamanoBytes = 1_024,
            huellaSha256 = "abc123",
            capturadaEn = "2026-11-15T10:30:00Z",
            ubicacion = null
        )
    )
)

private fun siniestroRegistrado() = Siniestro(
    siniestroId = "SIN-E2E-NUEVO",
    polizaId = "POL-E2E-SIN",
    origen = OrigenSiniestro.MANUAL,
    estado = EstadoSiniestro.REGISTRADO,
    eventoId = null,
    fechaEvento = "2026-11-15",
    horaEvento = "10:30:00",
    lugar = "Bogotá",
    descripcion = "Daño cubierto durante el viaje.",
    estimacionDanos = "250000",
    moneda = "COP",
    registradoEn = "2026-11-15T10:35:00Z",
    tipoSiniestro = TipoSiniestro.ROBO_HURTO
)
