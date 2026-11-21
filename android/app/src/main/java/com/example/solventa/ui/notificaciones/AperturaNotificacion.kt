package com.example.solventa.ui.notificaciones

import android.content.Context
import android.content.Intent
import com.example.solventa.MainActivity
import com.example.solventa.domain.notificaciones.CLAVE_NOTIFICACION_ID
import com.example.solventa.domain.notificaciones.CLAVE_POLIZA_ID
import com.example.solventa.domain.notificaciones.CLAVE_SINIESTRO_ID
import com.example.solventa.domain.notificaciones.CLAVE_TIPO
import com.example.solventa.domain.notificaciones.DestinoNotificacion
import com.example.solventa.domain.notificaciones.TipoNotificacion
import com.example.solventa.domain.notificaciones.destinoDe

/**
 * Lo que se pidió abrir al tocar una notificación del sistema: a dónde ir y cuál era, para
 * marcarla como leída.
 */
data class AperturaNotificacion(
    val destino: DestinoNotificacion,
    val notificacionId: String?
)

/**
 * Cómo la app abre el destino de una notificación a partir de un [Intent] (HU05).
 *
 * Las claves de los extras son las mismas que manda el backend en el push (`tipo`, `poliza_id`,
 * `siniestro_id`, `notificacion_id`): cuando la app está en segundo plano, Firebase muestra la
 * notificación por su cuenta y, al tocarla, abre la app con esos datos como extras del intent.
 */
object IntentsNotificacion {

    /** Lee cómo se abrió la app. Devuelve null si no viene de una notificación de Solventa. */
    fun apertura(intent: Intent?): AperturaNotificacion? {
        val extras = intent?.extras ?: return null
        val tipo = TipoNotificacion.desdeCodigo(extras.getString(CLAVE_TIPO)) ?: return null
        val datos = listOf(CLAVE_POLIZA_ID, CLAVE_SINIESTRO_ID)
            .mapNotNull { clave -> extras.getString(clave)?.let { clave to it } }
            .toMap()
        return AperturaNotificacion(
            destino = destinoDe(tipo, datos),
            notificacionId = extras.getString(CLAVE_NOTIFICACION_ID)?.takeIf(String::isNotBlank)
        )
    }

    /**
     * El intent que abre la app en el destino de una notificación. Lo usa el servicio de mensajería
     * cuando la app está abierta y es ella quien muestra la notificación.
     */
    fun crear(contexto: Context, datos: Map<String, String>): Intent =
        Intent(contexto, MainActivity::class.java).apply {
            // Si la app ya está abierta, se reutiliza en vez de abrir otra copia encima.
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or
                Intent.FLAG_ACTIVITY_CLEAR_TOP or
                Intent.FLAG_ACTIVITY_SINGLE_TOP
            datos.forEach { (clave, valor) -> putExtra(clave, valor) }
        }
}
