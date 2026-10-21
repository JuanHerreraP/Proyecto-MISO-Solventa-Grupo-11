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
class HomeScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private val eventos = mutableListOf<String>()
    private val perfil = Perfil("u-1", "Ana", "Pérez", "ana@gmail.com", "CLIENTE")

    private fun mostrar(
        biometriaActivada: Boolean = false,
        biometriaDisponible: Boolean = true,
        ofrecerActivar: Boolean = false,
        mensaje: String? = null,
        cerrandoSesion: Boolean = false
    ) {
        compose.setContent {
            SolventaTheme {
                HomeScreen(
                    perfil = perfil,
                    biometriaActivada = biometriaActivada,
                    biometriaDisponible = biometriaDisponible,
                    ofrecerActivarBiometria = ofrecerActivar,
                    mensaje = mensaje,
                    cerrandoSesion = cerrandoSesion,
                    onActivarBiometria = { eventos += "activar" },
                    onSolicitarActivacion = { eventos += "solicitar" },
                    onDescartarActivacion = { eventos += "descartar" },
                    onCerrarSesion = { eventos += "cerrar" }
                )
            }
        }
    }

    @Test
    fun muestraLosDatosDelClienteYPermiteCerrarSesion() {
        mostrar(mensaje = "Bienvenida")

        compose.onNodeWithText("Hola, Ana").assertIsDisplayed()
        compose.onNodeWithText("Ana Pérez").assertIsDisplayed()
        compose.onNodeWithText("ana@gmail.com").assertIsDisplayed()
        compose.onNodeWithText("Ingreso con huella desactivado").assertIsDisplayed()
        compose.onNodeWithText("Bienvenida").assertIsDisplayed()

        compose.boton("Cerrar sesión").performClick()

        assertEquals(listOf("cerrar"), eventos)
    }

    @Test
    fun sinHuellaActivadaOfreceActivarla() {
        mostrar()

        compose.boton("Activar ingreso con huella").performClick()

        assertEquals(listOf("solicitar"), eventos)
    }

    @Test
    fun conHuellaActivadaNoOfreceActivarla() {
        mostrar(biometriaActivada = true)

        compose.onNodeWithText("Ingreso con huella activado").assertIsDisplayed()
        compose.onNodeWithText("Activar ingreso con huella").assertDoesNotExist()
    }

    @Test
    fun sinBiometriaEnElDispositivoNoOfreceActivarla() {
        mostrar(biometriaDisponible = false)

        compose.onNodeWithText("Activar ingreso con huella").assertDoesNotExist()
    }

    @Test
    fun elDialogoDeActivacionPermiteActivar() {
        mostrar(ofrecerActivar = true)

        compose.onNodeWithText("¿Activar ingreso con huella?").assertIsDisplayed()
        compose.boton("Activar").performClick()

        assertEquals(listOf("activar"), eventos)
    }

    @Test
    fun elDialogoDeActivacionPermiteDecirAhoraNo() {
        mostrar(ofrecerActivar = true)

        compose.boton("Ahora no").performClick()

        assertEquals(listOf("descartar"), eventos)
    }

    @Test
    fun mientrasCierraSesionElBotonMuestraElProgreso() {
        mostrar(cerrandoSesion = true)

        compose.onNodeWithText("Cerrar sesión").assertDoesNotExist()
    }
}
