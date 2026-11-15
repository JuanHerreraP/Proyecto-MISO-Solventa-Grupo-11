package com.example.solventa.ui.asistencias

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.solventa.data.local.FuenteUbicacionActual
import com.example.solventa.domain.asistencias.AsistenciasCoordinator
import com.example.solventa.domain.asistencias.EstadoAsistencias
import com.example.solventa.domain.asistencias.PrestadorCercano
import com.example.solventa.domain.asistencias.ServicioAsistencia
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Puente entre la pantalla de asistencia en sitio (HU06) y su coordinador. Obtiene la ubicación
 * de una [FuenteUbicacionActual] y se la pasa al coordinador: la pantalla nunca toca el GPS.
 */
class AsistenciasViewModel(
    private val coordinador: AsistenciasCoordinator,
    private val ubicacion: FuenteUbicacionActual
) : ViewModel() {

    private val _estado = MutableStateFlow(coordinador.estado)
    val estado: StateFlow<EstadoAsistencias> = _estado.asStateFlow()

    init {
        coordinador.observador = { _estado.value = it }
    }

    fun tienePermisoUbicacion(): Boolean = ubicacion.tienePermiso()

    fun seleccionarPoliza(polizaId: String, etiqueta: String) {
        viewModelScope.launch { coordinador.seleccionarPoliza(polizaId, etiqueta) }
    }

    fun seleccionarServicio(servicio: ServicioAsistencia) = coordinador.seleccionarServicio(servicio)

    fun permisoDenegado() = coordinador.permisoDenegado()

    /** Obtiene la ubicación actual y busca prestadores; si no hay ubicación, lo informa. */
    fun buscarPrestadores(radioKm: Double? = null) {
        viewModelScope.launch {
            val actual = ubicacion.ubicacionActual()
            coordinador.buscarPrestadores(actual, radioKm ?: estado.value.radioKm)
        }
    }

    fun seleccionarPrestador(prestador: PrestadorCercano) =
        coordinador.seleccionarPrestador(prestador)

    fun volverAPrestadores() = coordinador.volverAPrestadores()

    fun solicitar(observaciones: String?) {
        viewModelScope.launch { coordinador.solicitar(observaciones) }
    }

    fun cargarAsistencias() {
        viewModelScope.launch { coordinador.cargarAsistencias() }
    }

    fun cancelar(asistenciaId: String) {
        viewModelScope.launch { coordinador.cancelar(asistenciaId) }
    }

    fun irAMisAsistencias() = coordinador.irAMisAsistencias()

    fun reiniciarFlujo() = coordinador.reiniciarFlujo()

    fun consumirError() = coordinador.consumirError()

    fun consumirAviso() = coordinador.consumirAviso()

    fun limpiar() = coordinador.limpiar()

    override fun onCleared() {
        coordinador.observador = null
    }

    class Fabrica(
        private val crearCoordinador: () -> AsistenciasCoordinator,
        private val crearUbicacion: () -> FuenteUbicacionActual
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            AsistenciasViewModel(crearCoordinador(), crearUbicacion()) as T
    }
}
