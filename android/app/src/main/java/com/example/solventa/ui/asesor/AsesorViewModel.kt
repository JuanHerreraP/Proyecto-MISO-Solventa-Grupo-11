package com.example.solventa.ui.asesor

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.solventa.domain.asesor.AsesorCoordinator
import com.example.solventa.domain.asesor.ClienteDeAsesor
import com.example.solventa.domain.asesor.DatosNuevoAnalista
import com.example.solventa.domain.asesor.DatosNuevoAsesor
import com.example.solventa.domain.asesor.EstadoAsesor
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class AsesorViewModel(private val coordinador: AsesorCoordinator) : ViewModel() {

    private val _estado = MutableStateFlow(coordinador.estado)
    val estado: StateFlow<EstadoAsesor> = _estado.asStateFlow()

    init {
        coordinador.observador = { _estado.value = it }
    }

    fun cargarClientes() {
        viewModelScope.launch { coordinador.cargarClientes() }
    }

    fun asociarCliente(email: String) {
        viewModelScope.launch { coordinador.asociarCliente(email) }
    }

    fun seleccionarCliente(cliente: ClienteDeAsesor) {
        viewModelScope.launch { coordinador.seleccionarCliente(cliente) }
    }

    fun crearAsesor(datos: DatosNuevoAsesor) {
        viewModelScope.launch { coordinador.crearAsesor(datos) }
    }

    fun crearAnalista(datos: DatosNuevoAnalista) {
        viewModelScope.launch { coordinador.crearAnalistaCumplimiento(datos) }
    }

    fun consumirClienteAsociado() = coordinador.consumirClienteAsociado()

    fun consumirErrorAsociar() = coordinador.consumirErrorAsociar()

    fun consumirAsesorCreado() = coordinador.consumirAsesorCreado()

    fun consumirErrorCrearAsesor() = coordinador.consumirErrorCrearAsesor()

    fun consumirAnalistaCreado() = coordinador.consumirAnalistaCreado()

    fun consumirErrorCrearAnalista() = coordinador.consumirErrorCrearAnalista()

    fun limpiarSeleccion() = coordinador.limpiarSeleccion()

    fun limpiar() = coordinador.limpiar()

    override fun onCleared() {
        coordinador.observador = null
    }

    class Fabrica(private val crear: () -> AsesorCoordinator) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            AsesorViewModel(crear()) as T
    }
}
