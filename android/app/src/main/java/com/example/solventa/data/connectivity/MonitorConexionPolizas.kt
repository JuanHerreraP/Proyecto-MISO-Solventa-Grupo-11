package com.example.solventa.data.connectivity

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import com.example.solventa.domain.polizas.SincronizadorPolizas
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

/** Ejecuta la sincronización cuando Android informa que la red predeterminada está disponible. */
class MonitorConexionPolizas(
    context: Context,
    private val alcance: CoroutineScope,
    private val sincronizador: SincronizadorPolizas
) {
    private val conectividad =
        context.applicationContext.getSystemService(ConnectivityManager::class.java)
    private var registrado = false
    private var trabajo: Job? = null

    private val callback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) {
            trabajo?.cancel()
            trabajo = alcance.launch { sincronizador.ejecutar() }
        }
    }

    fun iniciar() {
        if (registrado) return
        conectividad.registerDefaultNetworkCallback(callback)
        registrado = true
    }

    fun detener() {
        trabajo?.cancel()
        trabajo = null
        if (registrado) {
            conectividad.unregisterNetworkCallback(callback)
            registrado = false
        }
    }
}
