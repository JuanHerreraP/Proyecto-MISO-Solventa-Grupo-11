package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import com.example.solventa.domain.polizas.Certificado
import com.example.solventa.domain.polizas.EstadoPoliza
import com.example.solventa.domain.polizas.certificado
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class CertificateScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private val eventos = mutableListOf<String>()

    private fun mostrar(
        certificado: Certificado?,
        cargando: Boolean = false,
        error: String? = null,
        descargandoDocumento: Boolean = false,
        compartiendo: Boolean = false,
        mensaje: String? = null
    ) {
        compose.setContent {
            SolventaTheme {
                CertificateScreen(
                    certificado = certificado,
                    cargando = cargando,
                    error = error,
                    descargandoDocumento = descargandoDocumento,
                    compartiendo = compartiendo,
                    mensaje = mensaje,
                    onVerDocumento = { eventos += "documento" },
                    onCompartir = { eventos += "compartir" },
                    onVerHistorial = { eventos += "historial" },
                    onReintentar = { eventos += "reintentar" },
                    onVolver = { eventos += "volver" }
                )
            }
        }
    }

    private fun abrirCertificado() =
        compose.boton("Ver certificado y QR").performScrollTo().performClick()

    @Test
    fun muestraElResumenYLosBotonesDeGestion() {
        mostrar(certificado())

        compose.onNodeWithText("Coberturas").assertIsDisplayed()
        compose.onNodeWithText("Exclusiones principales").performScrollTo().assertIsDisplayed()
        compose.boton("Ver certificado y QR").performScrollTo().assertIsDisplayed()
        compose.boton("Consultar movimientos").performScrollTo().assertIsDisplayed()
        compose.boton("Renovar").performScrollTo().performClick()
        compose.boton("Cancelar").performScrollTo().assertIsDisplayed()
    }

    @Test
    fun unaPolizaInactivaNoOfreceRenovarNiCancelar() {
        mostrar(certificado(estado = EstadoPoliza.CANCELADA))

        compose.onNodeWithText("Renovar").assertDoesNotExist()
        compose.onNodeWithText("Cancelar").assertDoesNotExist()
    }

    @Test
    fun muestraElQrElNumeroYLosDatosDelCertificado() {
        mostrar(certificado())
        abrirCertificado()

        compose.onNodeWithText("Número de póliza").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Ana Pérez").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("CC ****5678").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Suma asegurada $40.000.000", substring = true)
            .performScrollTo()
            .assertIsDisplayed()
        compose.onNodeWithContentDescription("Código QR de la póliza SOL-VJ-0001")
            .performScrollTo()
            .assertIsDisplayed()
    }

    @Test
    fun permiteCompartirElCertificado() {
        mostrar(certificado())
        abrirCertificado()

        compose.boton("Compartir certificado").performScrollTo().performClick()

        assertEquals(listOf("compartir"), eventos)
    }

    @Test
    fun muestraExclusionesYPermiteAbrirElDocumento() {
        mostrar(certificado())
        abrirCertificado()

        compose.onNodeWithText("Viajes contra recomendación médica", substring = true)
            .performScrollTo()
            .assertIsDisplayed()
        compose.boton("Ver documento PDF").performScrollTo().performClick()

        assertEquals(listOf("documento"), eventos)
    }

    @Test
    fun permiteAbrirElHistorialDeLaPoliza() {
        mostrar(certificado())

        compose.boton("Consultar movimientos").performScrollTo().performClick()

        assertEquals(listOf("historial"), eventos)
    }

    @Test
    fun mientrasGeneraElEnlaceNoSePuedeVolverACompartir() {
        mostrar(certificado(), compartiendo = true)
        abrirCertificado()

        compose.onNodeWithText("Compartir certificado").assertDoesNotExist()
    }

    @Test
    fun unaPolizaInactivaLoDiceClaramente() {
        mostrar(certificado(estado = EstadoPoliza.VENCIDA))

        compose.onNodeWithText("Vencida").assertIsDisplayed()
        compose.onNodeWithText("Esta póliza ya no está vigente", substring = true).assertIsDisplayed()
    }

    @Test
    fun muestraElAvisoCuandoNoSePudoCompartir() {
        mostrar(certificado(), mensaje = "No pudimos generar el enlace")

        compose.onNodeWithText("No pudimos generar el enlace").performScrollTo().assertIsDisplayed()
    }

    @Test
    fun conErrorPermiteReintentar() {
        mostrar(certificado = null, error = "No encontramos esa póliza en tu billetera.")

        compose.onNodeWithText("No encontramos esa póliza en tu billetera.").assertIsDisplayed()
        compose.boton("Reintentar").performClick()

        assertEquals(listOf("reintentar"), eventos)
    }

    @Test
    fun mientrasCargaMuestraElProgreso() {
        mostrar(certificado = null, cargando = true)

        compose.onNodeWithContentDescription("Cargando el certificado").assertIsDisplayed()
    }
}
