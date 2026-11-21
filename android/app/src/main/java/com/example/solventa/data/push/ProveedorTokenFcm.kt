package com.example.solventa.data.push

import com.example.solventa.domain.notificaciones.ProveedorTokenPush
import com.google.android.gms.tasks.Task
import com.google.firebase.messaging.FirebaseMessaging
import kotlin.coroutines.resume
import kotlinx.coroutines.suspendCancellableCoroutine

/** El token de push de este teléfono, pedido a Firebase Cloud Messaging. */
class ProveedorTokenFcm(
    private val mensajeria: () -> FirebaseMessaging = { FirebaseMessaging.getInstance() }
) : ProveedorTokenPush {

    /** Null si Google no responde (sin servicios de Google o sin red): la bandeja sigue funcionando. */
    override suspend fun token(): String? = runCatching { mensajeria().token.esperar() }.getOrNull()

    /** Borra el token: el siguiente usuario que inicie sesión en este teléfono recibe uno nuevo. */
    override suspend fun olvidar() {
        runCatching { mensajeria().deleteToken().esperar() }
    }
}

private suspend fun <T> Task<T>.esperar(): T? = suspendCancellableCoroutine { continuacion ->
    addOnCompleteListener { tarea ->
        continuacion.resume(if (tarea.isSuccessful) tarea.result else null)
    }
}
