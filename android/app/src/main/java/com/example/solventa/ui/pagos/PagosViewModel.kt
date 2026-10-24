package com.example.solventa.ui.pagos

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.solventa.domain.pagos.EstadoPagos
import com.example.solventa.domain.pagos.PagosCoordinator
import com.example.solventa.domain.pagos.SolicitudPago
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class PagosViewModel(private val coordinador: PagosCoordinator) : ViewModel() {
    private val _estado = MutableStateFlow(coordinador.estado)
    val estado: StateFlow<EstadoPagos> = _estado.asStateFlow()

    init {
        coordinador.observador = { _estado.value = it }
    }

    fun pagar(solicitud: SolicitudPago) {
        viewModelScope.launch { coordinador.pagar(solicitud) }
    }

    fun consultar(pagoId: String) {
        viewModelScope.launch { coordinador.consultar(pagoId) }
    }

    fun listar() {
        viewModelScope.launch { coordinador.listar() }
    }

    fun prepararReintento() = coordinador.prepararReintento()

    fun limpiar() = coordinador.limpiar()

    override fun onCleared() {
        coordinador.observador = null
    }

    class Fabrica(private val crear: () -> PagosCoordinator) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            PagosViewModel(crear()) as T
    }
}
