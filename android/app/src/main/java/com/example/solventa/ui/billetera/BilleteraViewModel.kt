package com.example.solventa.ui.billetera

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.solventa.domain.polizas.BilleteraCoordinator
import com.example.solventa.domain.polizas.EstadoBilletera
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class BilleteraViewModel(private val coordinador: BilleteraCoordinator) : ViewModel() {

    private val _estado = MutableStateFlow(coordinador.estado)
    val estado: StateFlow<EstadoBilletera> = _estado.asStateFlow()

    init {
        coordinador.observador = { _estado.value = it }
    }

    fun cargar() {
        viewModelScope.launch { coordinador.cargar() }
    }

    fun verCertificado(polizaId: String) {
        viewModelScope.launch { coordinador.verCertificado(polizaId) }
    }

    fun compartir(polizaId: String) {
        viewModelScope.launch { coordinador.compartir(polizaId) }
    }

    fun enlaceCompartido() = coordinador.enlaceCompartido()

    fun consumirMensaje() = coordinador.consumirMensaje()

    fun cerrarCertificado() = coordinador.cerrarCertificado()

    fun limpiar() = coordinador.limpiar()

    override fun onCleared() {
        coordinador.observador = null
    }

    class Fabrica(private val crear: () -> BilleteraCoordinator) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            BilleteraViewModel(crear()) as T
    }
}
