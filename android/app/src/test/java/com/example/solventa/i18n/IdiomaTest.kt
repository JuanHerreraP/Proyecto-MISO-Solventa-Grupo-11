package com.example.solventa.i18n

import android.content.Context
import android.content.res.Configuration
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.core.app.ApplicationProvider
import com.example.solventa.R
import com.example.solventa.domain.polizas.Formatos
import com.example.solventa.ui.screens.SyncStatusBanner
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.util.Locale

/** Internacionalización: español por defecto, inglés a elección del usuario, mismos recursos en ambos. */
@RunWith(RobolectricTestRunner::class)
class IdiomaTest {
    @get:Rule
    val compose = createComposeRule()

    private val app: Context = ApplicationProvider.getApplicationContext()

    @After
    fun volverAlEspanol() {
        Idioma.establecer(app, Idioma.Opcion.ESPANOL)
    }

    @Test
    fun usaEspanolDeColombiaPorDefecto() {
        assertEquals(Idioma.Opcion.ESPANOL, Idioma.actual)
        assertEquals(Locale.forLanguageTag("es-CO"), Idioma.locale())
        assertEquals("Perfil", tr(R.string.home_perfil))
        assertEquals("Hola, Ana", tr(R.string.advisor_home_hola, "Ana"))
        assertFalse(Formatos.ingles)
        assertEquals("1 oct 2026", Formatos.fecha("2026-10-01"))
        assertEquals("$40.000.000", Formatos.dinero("40000000.00", "COP"))
    }

    @Test
    fun alElegirInglesCambianTextosYFormatosYSeRecuerdaLaEleccion() {
        Idioma.establecer(app, Idioma.Opcion.INGLES)

        assertEquals("Profile", tr(R.string.home_perfil))
        assertEquals("Hello, Ana", tr(R.string.advisor_home_hola, "Ana"))
        assertEquals(Locale.forLanguageTag("en-US"), Idioma.locale())
        assertEquals("Oct 1, 2026", Formatos.fecha("2026-10-01"))
        assertEquals("$1,234.50", Formatos.dinero("1234.50", "COP"))
        assertEquals("Active", Formatos.estado(com.example.solventa.domain.polizas.EstadoPoliza.VIGENTE))

        // Al reiniciar la app se conserva el idioma elegido.
        Idioma.iniciar(app)
        assertEquals(Idioma.Opcion.INGLES, Idioma.actual)
    }

    @Test
    fun laInterfazSePintaEnElIdiomaElegido() {
        Idioma.establecer(app, Idioma.Opcion.INGLES)

        compose.setContent { SyncStatusBanner(sinConexion = true, ultimaSincronizacionMs = null) }

        compose.onNodeWithText("Data available offline").assertExists()
    }

    @Test
    fun cadaTextoTieneTraduccionAlInglesConLosMismosArgumentos() {
        val espanol = recursos(Locale.forLanguageTag("es-CO"))
        val ingles = recursos(Locale.forLanguageTag("en-US"))
        val argumentos = Regex("%[0-9]+[$]s")
        val ids = R.string::class.java.fields.filter { it.name != "app_name" }.map { it.name to it.getInt(null) }

        assertTrue("Debe haber textos externalizados", ids.size > 400)
        for ((nombre, id) in ids) {
            val es = espanol.getString(id)
            val en = ingles.getString(id)
            assertTrue("$nombre sin texto en inglés", en.isNotBlank())
            assertEquals(nombre, argumentos.findAll(es).map { it.value }.sorted().toList(), argumentos.findAll(en).map { it.value }.sorted().toList())
        }
        // Algunos textos deben cambiar de verdad entre idiomas.
        assertTrue(ids.count { (_, id) -> espanol.getString(id) != ingles.getString(id) } > ids.size * 0.9)
    }

    private fun recursos(locale: Locale) = app.createConfigurationContext(
        Configuration(app.resources.configuration).apply { setLocale(locale) }
    ).resources
}
