package com.example.solventa.ui.siniestros

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.solventa.domain.siniestros.EstadoSiniestros
import com.example.solventa.domain.siniestros.SiniestrosCoordinator
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class SiniestrosViewModel(private val coordinador: SiniestrosCoordinator) : ViewModel() {

    private val _estado = MutableStateFlow(coordinador.estado)
    val estado: StateFlow<EstadoSiniestros> = _estado.asStateFlow()

    init {
        coordinador.observador = { _estado.value = it }
    }

    fun cargar() {
        viewModelScope.launch { coordinador.cargar() }
    }

    fun registrar(solicitud: com.example.solventa.domain.siniestros.SolicitudSiniestro) {
        viewModelScope.launch { coordinador.registrar(solicitud) }
    }

    fun consumirRegistroExitoso() = coordinador.consumirRegistroExitoso()

    fun consumirErrorFormulario() = coordinador.consumirErrorFormulario()

    fun consumirMensaje() = coordinador.consumirMensaje()

    fun limpiar() = coordinador.limpiar()

    override fun onCleared() {
        coordinador.observador = null
    }

    class Fabrica(private val crear: () -> SiniestrosCoordinator) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            SiniestrosViewModel(crear()) as T
    }
}
