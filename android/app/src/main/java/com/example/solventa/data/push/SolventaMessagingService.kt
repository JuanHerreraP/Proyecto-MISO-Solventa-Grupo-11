package com.example.solventa.data.push

import android.Manifest
import android.annotation.SuppressLint
import android.app.PendingIntent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.example.solventa.R
import com.example.solventa.ui.notificaciones.IntentsNotificacion
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

/** Quién se entera de que FCM entregó un token nuevo. Lo asigna la pantalla principal. */
object NuevoTokenPush {
    @Volatile
    var alRecibir: ((String) -> Unit)? = null
}

/**
 * Recibe los push de Firebase (HU05).
 *
 * - Con la app en segundo plano Firebase muestra la notificación por su cuenta, en el canal que
 *   indica el backend, y al tocarla abre la app con los datos como extras del intent.
 * - Con la app abierta llega aquí y se muestra igual. Lleva la misma etiqueta que mandó el backend,
 *   así que un resumen del mismo grupo reemplaza al aviso anterior en vez de apilarse.
 */
class SolventaMessagingService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        // Sin sesión no hay a quién asociarlo: el token se pide de nuevo al iniciar sesión.
        NuevoTokenPush.alRecibir?.invoke(token)
    }

    @SuppressLint("MissingPermission") // Se comprueba con puedeNotificar() justo antes.
    override fun onMessageReceived(mensaje: RemoteMessage) {
        val aviso = mensaje.notification ?: return
        if (!puedeNotificar()) return

        CanalNotificaciones.crear(this)
        val intent = IntentsNotificacion.crear(this, mensaje.data)
        val abrir = PendingIntent.getActivity(
            this,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val notificacion = NotificationCompat.Builder(this, CanalNotificaciones.ID)
            .setSmallIcon(R.drawable.ic_stat_notificacion)
            .setContentTitle(aviso.title)
            .setContentText(aviso.body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(aviso.body))
            .setContentIntent(abrir)
            .setAutoCancel(true)
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .build()

        // La misma etiqueta y el mismo id reemplazan el aviso anterior del grupo.
        NotificationManagerCompat.from(this).notify(aviso.tag, ID_NOTIFICACION, notificacion)
    }

    private fun puedeNotificar(): Boolean {
        val permiso = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED
        return permiso && NotificationManagerCompat.from(this).areNotificationsEnabled()
    }

    private companion object {
        const val ID_NOTIFICACION = 1
    }
}
