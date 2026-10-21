package com.example.solventa.ui.screens

import android.app.Activity
import android.app.DatePickerDialog
import android.content.DialogInterface
import android.content.Intent
import android.graphics.Bitmap
import android.os.Looper
import android.provider.MediaStore
import androidx.activity.ComponentActivity
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.isToggleable
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import com.example.solventa.domain.auth.DatosRegistro
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.shadows.ShadowDialog

@RunWith(RobolectricTestRunner::class)
class RegisterScreenTest {
    @get:Rule
    val compose = createAndroidComposeRule<ComponentActivity>()

    private var enviado: DatosRegistro? = null
    private val eventos = mutableListOf<String>()

    private fun mostrar(cargando: Boolean = false, mensaje: String? = null) {
        compose.setContent {
            SolventaTheme {
                RegisterScreen(
                    onBackClick = { eventos += "volver" },
                    onRegisterSubmit = { enviado = it },
                    onLoginClick = { eventos += "ingresar" },
                    cargando = cargando,
                    mensaje = mensaje
                )
            }
        }
    }

    private fun escribir(etiqueta: String, valor: String) {
        compose.campo(etiqueta).performScrollTo().performTextInput(valor)
    }

    private fun elegirDocumento(opcion: String) {
        compose.onNodeWithContentDescription("Abrir lista de tipos de documento").performScrollTo().performClick()
        compose.onNodeWithText(opcion).performClick()
    }

    private fun elegirFecha(anio: Int, mes: Int, dia: Int) {
        compose.onNodeWithContentDescription("Seleccionar fecha").performScrollTo().performClick()
        shadowOf(Looper.getMainLooper()).idle()
        val dialogo = ShadowDialog.getLatestDialog() as DatePickerDialog
        dialogo.updateDate(anio, mes, dia)
        dialogo.getButton(DialogInterface.BUTTON_POSITIVE).performClick()
        shadowOf(Looper.getMainLooper()).idle()
        compose.waitForIdle()
    }

    private fun llenarFormularioValido() {
        escribir("Nombres", "Ana")
        escribir("Apellidos", "Pérez")
        elegirDocumento("CC · Cédula de ciudadanía")
        escribir("Número de documento", "1000000001")
        elegirFecha(1999, 0, 15)
        escribir("Correo electrónico", "ana@gmail.com")
        escribir("Celular", "3001234567")
        escribir("Contraseña", "Password123")
        compose.onNode(isToggleable()).performScrollTo().performClick()
    }

    /** Responde a la cámara del sistema con una foto o con una cancelación. */
    private fun responderCamara(foto: Bitmap?) {
        val sombra = shadowOf(compose.activity)
        val pedido = checkNotNull(sombra.nextStartedActivityForResult) { "No se abrió la cámara" }
        assertEquals(MediaStore.ACTION_IMAGE_CAPTURE, pedido.intent.action)
        if (foto != null) {
            sombra.receiveResult(pedido.intent, Activity.RESULT_OK, Intent().putExtra("data", foto))
        } else {
            sombra.receiveResult(pedido.intent, Activity.RESULT_CANCELED, null)
        }
        compose.waitForIdle()
    }

    @Test
    fun formularioVacioNoPermiteTomarSelfieNiRegistrarse() {
        mostrar()

        compose.boton("Tomar selfie").performScrollTo().assertIsNotEnabled()
        compose.boton("Validar identidad y crear cuenta").performScrollTo().assertIsNotEnabled()
        compose.onNodeWithText("Completa todos los campos", substring = true).performScrollTo().assertIsDisplayed()
    }

    @Test
    fun formularioCompletoConSelfieEnviaLosDatos() {
        mostrar()
        llenarFormularioValido()

        compose.boton("Tomar selfie").performScrollTo().assertIsEnabled().performClick()
        responderCamara(Bitmap.createBitmap(8, 8, Bitmap.Config.ARGB_8888))

        compose.onNodeWithContentDescription("Vista previa de la selfie").performScrollTo().assertIsDisplayed()
        compose.boton("Tomar otra selfie").performScrollTo().assertIsDisplayed()
        compose.boton("Validar identidad y crear cuenta").performScrollTo().assertIsEnabled().performClick()

        val datos = assertNotNullYDevolver(enviado)
        assertEquals("Ana", datos.nombre)
        assertEquals("Pérez", datos.apellido)
        assertEquals("CC", datos.tipoDocumento)
        assertEquals("1000000001", datos.numeroDocumento)
        assertEquals("1999-01-15", datos.fechaNacimiento)
        assertEquals("ana@gmail.com", datos.email)
        assertEquals("3001234567", datos.celular)
        assertEquals("Password123", datos.password)
        assertTrue(datos.selfieBase64.isNotEmpty())
    }

    @Test
    fun cancelarLaCamaraMuestraUnError() {
        mostrar()
        llenarFormularioValido()

        compose.boton("Tomar selfie").performScrollTo().performClick()
        responderCamara(null)

        compose.onNodeWithText("No se capturó la selfie. Inténtalo de nuevo.").performScrollTo().assertIsDisplayed()
        compose.boton("Validar identidad y crear cuenta").performScrollTo().assertIsNotEnabled()
    }

    @Test
    fun camposInvalidosMuestranSuError() {
        mostrar()

        escribir("Nombres", "A1")
        escribir("Correo electrónico", "correo-malo")
        escribir("Celular", "123")
        escribir("Contraseña", "corta")

        compose.onNodeWithText("Solo letras, espacios, guion o apóstrofe.").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Ingresa un correo electrónico válido.").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Debe tener 10 dígitos y empezar por 3.").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Debe tener al menos 8 caracteres.").performScrollTo().assertIsDisplayed()
    }

    @Test
    fun elNumeroDeDocumentoSeFiltraSegunElTipo() {
        mostrar()

        elegirDocumento("CC · Cédula de ciudadanía")
        escribir("Número de documento", "12ab3")
        compose.onNodeWithText("Solo números, entre 5 y 12 dígitos.").performScrollTo().assertIsDisplayed()

        // Cambiar de tipo limpia el número y el pasaporte acepta letras.
        elegirDocumento("PAS · Pasaporte")
        escribir("Número de documento", "AB12")
        compose.onNodeWithText("Solo letras y números, entre 6 y 12 caracteres.").performScrollTo().assertIsDisplayed()
    }

    @Test
    fun laFechaElegidaEnElCalendarioSeMuestraEnFormatoIso() {
        mostrar()

        elegirFecha(1990, 5, 9)

        compose.onNodeWithText("1990-06-09").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Debes ser mayor de 18 años.").assertDoesNotExist()
    }

    @Test
    fun mensajeDelServidorYEnlacesFuncionan() {
        mostrar(mensaje = "La verificación no fue aprobada.")

        compose.onNodeWithText("La verificación no fue aprobada.").performScrollTo().assertIsDisplayed()
        compose.boton("¿Ya tienes cuenta? Iniciar sesión").performScrollTo().performClick()
        compose.onNodeWithContentDescription("Volver").performScrollTo().performClick()

        assertEquals(listOf("ingresar", "volver"), eventos)
    }

    @Test
    fun mientrasCargaNoSePuedeEnviar() {
        mostrar(cargando = true)

        compose.boton("Tomar selfie").performScrollTo().assertIsNotEnabled()
        compose.onNodeWithText("Validar identidad y crear cuenta").assertDoesNotExist()
    }

    private fun <T> assertNotNullYDevolver(valor: T?): T {
        assertNotNull(valor)
        return valor!!
    }
}
