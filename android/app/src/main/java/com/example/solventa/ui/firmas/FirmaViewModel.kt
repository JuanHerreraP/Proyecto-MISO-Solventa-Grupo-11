package com.example.solventa.ui.firmas

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.solventa.domain.firmas.EstadoFirma
import com.example.solventa.domain.firmas.FirmaCoordinator
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class FirmaViewModel(private val coordinador: FirmaCoordinator) : ViewModel() {
    private val _estado = MutableStateFlow(coordinador.estado)
    val estado: StateFlow<EstadoFirma> = _estado.asStateFlow()

    init {
        coordinador.observador = { _estado.value = it }
    }

    fun presentar(cotizacionId: String) = viewModelScope.launch { coordinador.presentar(cotizacionId) }
    fun solicitarCodigo(cotizacionId: String) = viewModelScope.launch { coordinador.solicitarCodigo(cotizacionId) }
    fun firmar(cotizacionId: String, codigo: String) = viewModelScope.launch { coordinador.firmar(cotizacionId, codigo) }
    fun limpiar() = coordinador.limpiar()

    override fun onCleared() {
        coordinador.observador = null
    }

    class Fabrica(private val crear: () -> FirmaCoordinator) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = FirmaViewModel(crear()) as T
    }
}
