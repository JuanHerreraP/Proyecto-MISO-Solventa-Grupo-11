package com.example.solventa.data.local

import android.annotation.SuppressLint
import android.content.Context
import com.example.solventa.domain.siniestros.Ubicacion
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource
import kotlin.coroutines.resume
import kotlinx.coroutines.suspendCancellableCoroutine

/**
 * Fuente de la ubicación actual para HU06, detrás de una abstracción testeable.
 *
 * La capa de UI/ViewModel depende de esta interfaz, no de los servicios de Google, para que las
 * reglas se puedan probar sin emulador. HU06 solo pide la ubicación cuando el cliente busca
 * asistencia: no hay rastreo continuo ni en segundo plano.
 */
interface FuenteUbicacionActual {
    fun tienePermiso(): Boolean

    /** Ubicación suficientemente actual, o null si no se puede obtener. */
    suspend fun ubicacionActual(): Ubicacion?
}

/**
 * Implementación con `FusedLocationProviderClient`: intenta una posición actual y, si no llega,
 * cae a la última conocida de [ProveedorUbicacion] (que no depende de los servicios de Google).
 */
class FuenteUbicacionFused(
    private val context: Context,
    private val ultimaConocida: ProveedorUbicacion = ProveedorUbicacion(context)
) : FuenteUbicacionActual {

    private val cliente by lazy { LocationServices.getFusedLocationProviderClient(context) }

    override fun tienePermiso(): Boolean = ultimaConocida.tienePermiso()

    @SuppressLint("MissingPermission") // El permiso se verifica en tienePermiso().
    override suspend fun ubicacionActual(): Ubicacion? {
        if (!tienePermiso()) return null
        val actual = try {
            solicitarActual()
        } catch (error: SecurityException) {
            null
        } catch (error: Exception) {
            null
        }
        return actual ?: ultimaConocida.ultimaUbicacion()
    }

    @SuppressLint("MissingPermission")
    private suspend fun solicitarActual(): Ubicacion? = suspendCancellableCoroutine { cont ->
        val cancelacion = CancellationTokenSource()
        cont.invokeOnCancellation { cancelacion.cancel() }
        cliente
            .getCurrentLocation(Priority.PRIORITY_BALANCED_POWER_ACCURACY, cancelacion.token)
            .addOnSuccessListener { ubicacion ->
                cont.resume(
                    ubicacion?.let {
                        Ubicacion(
                            latitud = it.latitude,
                            longitud = it.longitude,
                            precisionMetros = if (it.hasAccuracy()) it.accuracy else null
                        )
                    }
                )
            }
            .addOnFailureListener { cont.resume(null) }
    }
}
