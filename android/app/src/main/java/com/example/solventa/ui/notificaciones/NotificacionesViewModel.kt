package com.example.solventa.ui.notificaciones

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.solventa.domain.notificaciones.EstadoNotificaciones
import com.example.solventa.domain.notificaciones.NotificacionesCoordinator
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull

class NotificacionesViewModel(private val coordinador: NotificacionesCoordinator) : ViewModel() {
    private val _estado = MutableStateFlow(coordinador.estado)
    val estado: StateFlow<EstadoNotificaciones> = _estado.asStateFlow()

    init {
        coordinador.observador = { _estado.value = it }
    }

    fun cargar() {
        viewModelScope.launch { coordinador.cargar() }
    }

    fun actualizarInsignia() {
        viewModelScope.launch { coordinador.actualizarInsignia() }
    }

    fun marcarLeida(notificacionId: String) {
        viewModelScope.launch { coordinador.marcarLeida(notificacionId) }
    }

    fun cargarPreferencia() {
        viewModelScope.launch { coordinador.cargarPreferencia() }
    }

    fun cambiarPreferencia(pushHabilitado: Boolean) {
        viewModelScope.launch { coordinador.cambiarPreferencia(pushHabilitado) }
    }

    /** Se llama al iniciar sesión: registra el token de push del teléfono, si lo hay. */
    fun registrarDispositivo() {
        viewModelScope.launch { coordinador.registrarDispositivo() }
    }

    fun registrarToken(tokenPush: String) {
        viewModelScope.launch { coordinador.registrarToken(tokenPush) }
    }

    /**
     * Da de baja el teléfono y luego ejecuta [alTerminar] (el cierre de sesión). La baja necesita la
     * sesión viva, así que va primero; si tarda más de [ESPERA_MAXIMA_MS] el cierre sigue igual.
     */
    fun cerrarSesionConBaja(alTerminar: () -> Unit) {
        viewModelScope.launch {
            withTimeoutOrNull(ESPERA_MAXIMA_MS) { coordinador.darDeBajaDispositivo() }
            alTerminar()
        }
    }

    fun limpiar() = coordinador.limpiar()

    override fun onCleared() {
        coordinador.observador = null
    }

    class Fabrica(private val crear: () -> NotificacionesCoordinator) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            NotificacionesViewModel(crear()) as T
    }

    private companion object {
        const val ESPERA_MAXIMA_MS = 3_000L
    }
}
