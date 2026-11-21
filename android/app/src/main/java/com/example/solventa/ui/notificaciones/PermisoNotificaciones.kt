package com.example.solventa.ui.notificaciones

import android.Manifest
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.LifecycleOwner

/**
 * Si la app puede mostrar notificaciones en este teléfono. Desde Android 13 hay que pedir el
 * permiso `POST_NOTIFICATIONS`; antes basta con que el cliente no las haya bloqueado en Ajustes.
 */
fun notificacionesPermitidas(contexto: Context): Boolean {
    val permiso = if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
        true
    } else {
        ContextCompat.checkSelfPermission(contexto, Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED
    }
    return permiso && androidx.core.app.NotificationManagerCompat.from(contexto).areNotificationsEnabled()
}

/** Abre los ajustes de notificaciones de la app, donde el cliente puede desbloquearlas. */
fun abrirAjustesDeNotificaciones(contexto: Context) {
    val intent = Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
        .putExtra(Settings.EXTRA_APP_PACKAGE, contexto.packageName)
        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    contexto.startActivity(intent)
}

/** El estado del permiso de notificaciones y cómo pedirlo, para una pantalla de la app. */
class SolicitudPermisoNotificaciones(
    val concedido: Boolean,
    val solicitar: () -> Unit,
    val abrirAjustes: () -> Unit
)

/**
 * Recuerda si las notificaciones están permitidas y ofrece pedirlas. Se vuelve a comprobar al
 * regresar a la app, por si el cliente las habilitó desde Ajustes.
 */
@Composable
fun rememberSolicitudPermisoNotificaciones(): SolicitudPermisoNotificaciones {
    val contexto = LocalContext.current
    var concedido by remember { mutableStateOf(notificacionesPermitidas(contexto)) }
    val lanzador = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {
        concedido = notificacionesPermitidas(contexto)
    }

    val duenoDelCiclo = remember(contexto) { contexto.buscarLifecycleOwner() }
    DisposableEffect(duenoDelCiclo) {
        val observador = LifecycleEventObserver { _, evento ->
            if (evento == Lifecycle.Event.ON_RESUME) concedido = notificacionesPermitidas(contexto)
        }
        duenoDelCiclo?.lifecycle?.addObserver(observador)
        onDispose { duenoDelCiclo?.lifecycle?.removeObserver(observador) }
    }

    return SolicitudPermisoNotificaciones(
        concedido = concedido,
        solicitar = {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                lanzador.launch(Manifest.permission.POST_NOTIFICATIONS)
            } else {
                // Antes de Android 13 no hay permiso que pedir: solo Ajustes puede desbloquearlas.
                abrirAjustesDeNotificaciones(contexto)
            }
        },
        abrirAjustes = { abrirAjustesDeNotificaciones(contexto) }
    )
}

private fun Context.buscarLifecycleOwner(): LifecycleOwner? {
    var actual: Context? = this
    while (actual is ContextWrapper) {
        if (actual is LifecycleOwner) return actual
        actual = actual.baseContext
    }
    return actual as? LifecycleOwner
}
