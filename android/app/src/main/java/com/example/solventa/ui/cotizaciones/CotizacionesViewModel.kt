package com.example.solventa.ui.cotizaciones

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.solventa.domain.cotizaciones.CotizacionesCoordinator
import com.example.solventa.domain.cotizaciones.EstadoCotizaciones
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class CotizacionesViewModel(private val coordinador: CotizacionesCoordinator) : ViewModel() {
    private val _estado = MutableStateFlow(coordinador.estado)
    val estado: StateFlow<EstadoCotizaciones> = _estado.asStateFlow()

    init {
        coordinador.observador = { _estado.value = it }
    }

    fun cotizar(clienteId: String, ramo: RamoCotizacion, valores: Map<String, String>) {
        viewModelScope.launch { coordinador.cotizar(clienteId, ramo, valores) }
    }

    fun limpiar() = coordinador.limpiar()

    override fun onCleared() {
        coordinador.observador = null
    }

    class Fabrica(private val crear: () -> CotizacionesCoordinator) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            CotizacionesViewModel(crear()) as T
    }
}

