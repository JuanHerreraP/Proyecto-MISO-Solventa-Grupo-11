package com.example.solventa.e2e.polizas

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.solventa.E2ETestActivity
import com.example.solventa.domain.polizas.Billetera
import com.example.solventa.domain.polizas.Certificado
import com.example.solventa.domain.polizas.EstadoPoliza
import com.example.solventa.domain.polizas.PolizaResumen
import com.example.solventa.ui.screens.CertificateScreen
import com.example.solventa.ui.screens.WalletScreen
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CertificadoYConexionE2ETest {
    @get:Rule val compose = createAndroidComposeRule<E2ETestActivity>()

    @Test
    fun certificadoPermiteAbrirPdfYCompartirEnlaceTemporal() {
        var pdfAbierto = 0
        var compartidos = 0

        compose.setContent {
            SolventaTheme {
                CertificateScreen(
                    certificado = certificado(),
                    cargando = false,
                    error = null,
                    descargandoDocumento = false,
                    compartiendo = false,
                    mensaje = null,
                    onVerDocumento = { pdfAbierto++ },
                    onCompartir = { compartidos++ },
                    onVerHistorial = {},
                    onReintentar = {},
                    onVolver = {}
                )
            }
        }

        compose.boton("Ver certificado y QR").performScrollTo().performClick()
        compose.boton("Ver documento PDF").performScrollTo().performClick()
        compose.boton("Compartir certificado").performScrollTo().performClick()

        assertEquals(1, pdfAbierto)
        assertEquals(1, compartidos)
    }

    @Test
    fun alRecuperarConexionSeActualizaSinOcultarLasPolizas() {
        val sinConexion = mutableStateOf(true)

        compose.setContent {
            SolventaTheme {
                WalletScreen(
                    billetera = billetera(),
                    cargando = false,
                    error = null,
                    sinConexion = sinConexion.value,
                    ultimaSincronizacionMs = 1_798_000_000_000L,
                    onVerPoliza = {},
                    onReintentar = {},
                    onVolver = {}
                )
            }
        }

        compose.onNodeWithContentDescription("Sin conexión").assertIsDisplayed()
        compose.runOnUiThread { sinConexion.value = false }

        compose.onNodeWithContentDescription("Datos actualizados").assertIsDisplayed()
        compose.onNodeWithText("Seguro de viaje").assertIsDisplayed()
    }
}

private fun androidx.compose.ui.test.SemanticsNodeInteractionsProvider.boton(texto: String) =
    onNode(hasText(texto) and hasClickAction())

private fun certificado() = Certificado(
    polizaId = "POL-E2E-CERT",
    numeroPoliza = "SOL-E2E-CERT",
    nombreRamo = "Seguro de viaje",
    estado = EstadoPoliza.VIGENTE,
    activa = true,
    titular = "Ana Pérez",
    documentoTitular = "CC 1234***",
    fechaInicio = "2026-11-13",
    fechaFin = "2026-11-27",
    coberturaPrincipal = "Asistencia integral de viaje",
    sumaAsegurada = "20000000",
    moneda = "COP",
    contenidoQr = "https://solventa.test/cert/POL-E2E-CERT",
    primaTotal = "84000",
    exclusionesPrincipales = listOf("Atenciones fuera de la vigencia declarada")
)

private fun billetera() = Billetera(
    polizas = listOf(
        PolizaResumen(
            polizaId = "POL-E2E-CERT",
            numeroPoliza = "SOL-E2E-CERT",
            ramo = "VIAJE",
            nombreRamo = "Seguro de viaje",
            estado = EstadoPoliza.VIGENTE,
            activa = true,
            fechaInicio = "2026-11-13",
            fechaFin = "2026-11-27",
            coberturaPrincipal = "Asistencia integral de viaje",
            emitidaEn = "2026-11-07T14:07:00Z"
        )
    ),
    totalVigentes = 1,
    totalInactivas = 0
)
