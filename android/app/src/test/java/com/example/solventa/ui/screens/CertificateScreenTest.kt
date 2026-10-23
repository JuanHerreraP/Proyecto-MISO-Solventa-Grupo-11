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
        compartiendo: Boolean = false,
        mensaje: String? = null
    ) {
        compose.setContent {
            SolventaTheme {
                CertificateScreen(
                    certificado = certificado,
                    cargando = cargando,
                    error = error,
                    compartiendo = compartiendo,
                    mensaje = mensaje,
                    onCompartir = { eventos += "compartir" },
                    onReintentar = { eventos += "reintentar" },
                    onVolver = { eventos += "volver" }
                )
            }
        }
    }

    @Test
    fun muestraElQrElNumeroYLosDatosDelCertificado() {
        mostrar(certificado())

        compose.onNodeWithContentDescription("Código QR de la póliza SOL-VJ-0001").assertIsDisplayed()
        compose.onNodeWithText("SOL-VJ-0001").assertIsDisplayed()
        compose.onNodeWithText("Ana Pérez").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("CC ****5678").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("$40.000.000").performScrollTo().assertIsDisplayed()
    }

    @Test
    fun permiteCompartirElCertificado() {
        mostrar(certificado())

        compose.boton("Compartir certificado").performScrollTo().performClick()

        assertEquals(listOf("compartir"), eventos)
    }

    @Test
    fun mientrasGeneraElEnlaceNoSePuedeVolverACompartir() {
        mostrar(certificado(), compartiendo = true)

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
