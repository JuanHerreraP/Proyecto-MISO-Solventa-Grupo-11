package com.example.solventa.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.solventa.biometric.FalloBiometrico
import com.example.solventa.domain.auth.AuthCoordinator
import com.example.solventa.domain.auth.DatosRegistro
import com.example.solventa.domain.auth.EstadoAuth
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class AuthViewModel(private val coordinador: AuthCoordinator) : ViewModel() {

    private val _estado = MutableStateFlow(coordinador.estado)
    val estado: StateFlow<EstadoAuth> = _estado.asStateFlow()

    init {
        coordinador.observador = { _estado.value = it }
    }

    fun ingresarConCredenciales(email: String, password: String) {
        viewModelScope.launch { coordinador.ingresarConCredenciales(email, password) }
    }

    fun registrar(datos: DatosRegistro) {
        viewModelScope.launch { coordinador.registrar(datos) }
    }

    fun solicitarIngresoBiometrico(): Boolean = coordinador.solicitarIngresoBiometrico()

    fun ingresarConBiometria() {
        viewModelScope.launch { coordinador.ingresarConBiometria() }
    }

    fun falloBiometrico(fallo: FalloBiometrico) = coordinador.falloBiometrico(fallo)

    fun huellaNoReconocida() = coordinador.huellaNoReconocida()

    fun solicitarActivacion() = coordinador.solicitarActivacion()

    fun prepararActivacion() = coordinador.prepararActivacion()

    fun activarBiometria() = coordinador.activarBiometria()

    fun descartarActivacion(mensaje: String? = null) = coordinador.descartarActivacion(mensaje)

    fun credencialesMostradas() = coordinador.credencialesMostradas()

    fun consumirMensaje() = coordinador.consumirMensaje()

    fun consumirRegistroCompletado() = coordinador.consumirRegistroCompletado()

    fun verificarExpiracion() = coordinador.verificarExpiracion()

    fun refrescarPerfil() {
        viewModelScope.launch { coordinador.refrescarPerfil() }
    }

    fun cerrarSesion() {
        viewModelScope.launch { coordinador.cerrarSesion() }
    }

    override fun onCleared() {
        coordinador.observador = null
    }

    class Fabrica(private val crear: () -> AuthCoordinator) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = AuthViewModel(crear()) as T
    }
}
