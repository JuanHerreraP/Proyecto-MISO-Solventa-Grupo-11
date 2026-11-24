package com.example.solventa.i18n

import android.app.Activity
import android.content.Context
import android.content.res.Configuration
import android.os.LocaleList
import androidx.annotation.StringRes
import com.example.solventa.domain.polizas.Formatos
import java.util.Locale

/**
 * Internacionalización de la app: español de Colombia (predeterminado) e inglés.
 *
 * Los textos viven en res/values/strings.xml (español) y res/values-en/strings.xml (inglés).
 * El idioma elegido se guarda en preferencias y se aplica a la actividad (attachBaseContext),
 * a los textos que se leen con [tr] y a los formatos de fecha y moneda.
 */
object Idioma {

    enum class Opcion(val codigo: String, val locale: Locale) {
        ESPANOL("es", Locale.forLanguageTag("es-CO")),
        INGLES("en", Locale.forLanguageTag("en-US"));

        companion object {
            fun desdeCodigo(codigo: String?): Opcion = entries.firstOrNull { it.codigo == codigo } ?: ESPANOL
        }
    }

    private const val PREFERENCIAS = "solventa_idioma"
    private const val CLAVE = "idioma"

    @Volatile
    private var contexto: Context? = null

    @Volatile
    var actual: Opcion = Opcion.ESPANOL
        private set

    /** Locale para formatear números y fechas en el idioma activo. */
    fun locale(): Locale = actual.locale

    /** Se llama al iniciar la aplicación: carga el idioma guardado. */
    fun iniciar(context: Context) {
        val app = context.applicationContext ?: context
        aplicar(app, leer(app))
    }

    /** Guarda el idioma y lo aplica a los textos y formatos que se lean desde ahora. */
    fun establecer(context: Context, opcion: Opcion) {
        val app = context.applicationContext ?: context
        app.getSharedPreferences(PREFERENCIAS, Context.MODE_PRIVATE)
            .edit().putString(CLAVE, opcion.codigo).apply()
        aplicar(app, opcion)
    }

    /** Cambia el idioma y recrea la actividad para pintar toda la interfaz de nuevo. */
    fun cambiar(activity: Activity, opcion: Opcion) {
        if (opcion == actual) return
        establecer(activity, opcion)
        activity.recreate()
    }

    /** Contexto de la actividad con el idioma guardado (para attachBaseContext). */
    fun envolver(base: Context): Context = localizar(base, leer(base))

    /** Texto del recurso en el idioma activo; acepta argumentos de formato (%1$s, %2$s…). */
    fun texto(@StringRes id: Int, vararg argumentos: Any?): String {
        val recursos = checkNotNull(contexto) { "Idioma.iniciar() no se ha llamado" }.resources
        return if (argumentos.isEmpty()) recursos.getString(id) else recursos.getString(id, *argumentos)
    }

    private fun aplicar(app: Context, opcion: Opcion) {
        actual = opcion
        contexto = localizar(app, opcion)
        Formatos.ingles = opcion == Opcion.INGLES
    }

    private fun leer(context: Context): Opcion = Opcion.desdeCodigo(
        context.getSharedPreferences(PREFERENCIAS, Context.MODE_PRIVATE).getString(CLAVE, null)
    )

    private fun localizar(base: Context, opcion: Opcion): Context {
        val configuracion = Configuration(base.resources.configuration).apply {
            setLocale(opcion.locale)
            setLocales(LocaleList(opcion.locale))
        }
        return base.createConfigurationContext(configuracion)
    }
}

/** Atajo de [Idioma.texto]: `tr(R.string.home_perfil)`. */
fun tr(@StringRes id: Int, vararg argumentos: Any?): String = Idioma.texto(id, *argumentos)
