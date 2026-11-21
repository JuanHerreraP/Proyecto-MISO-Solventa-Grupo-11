package com.example.solventa.data.push

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build

/** El canal de las notificaciones de Solventa. El backend lo nombra igual en cada push. */
object CanalNotificaciones {
    const val ID = "solventa_notificaciones"

    /** Lo crea si no existe. Desde Android 8 es obligatorio para poder mostrar avisos. */
    fun crear(contexto: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val gestor = contexto.getSystemService(NotificationManager::class.java) ?: return
        val canal = NotificationChannel(
            ID,
            "Avisos de Solventa",
            NotificationManager.IMPORTANCE_DEFAULT
        ).apply {
            description = "Pagos de tu seguro paramétrico, vencimientos de pólizas y cambios en tus siniestros."
            // Los avisos traen datos del cliente: en la pantalla de bloqueo no se muestra su contenido.
            lockscreenVisibility = android.app.Notification.VISIBILITY_PRIVATE
        }
        gestor.createNotificationChannel(canal)
    }
}
