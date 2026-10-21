package com.example.solventa.ui.auth

import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import com.example.solventa.biometric.FalloBiometrico
import com.example.solventa.domain.auth.AuthCoordinator
import com.example.solventa.domain.auth.BovedaFalsa
import com.example.solventa.domain.auth.DatosRegistro
import com.example.solventa.domain.auth.GatewayFalso
import com.example.solventa.domain.auth.MensajesAuth
import com.example.solventa.domain.auth.PERFIL_ANA
import com.example.solventa.domain.auth.RegistroCreado
import com.example.solventa.domain.auth.RelojFalso
import com.example.solventa.domain.auth.ResultadoApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/** El ViewModel solo delega en el coordinador y expone su estado como StateFlow. */
@OptIn(ExperimentalCoroutinesApi::class)
class AuthViewModelTest {
    private val gateway = GatewayFalso()
    private val reloj = RelojFalso()
    private lateinit var boveda: BovedaFalsa
    private lateinit var coordinador: AuthCoordinator
    private lateinit var viewModel: AuthViewModel

    private val datosRegistro = DatosRegistro(
        nombre = "Ana",
        apellido = "Perez",
        email = "ana@gmail.com",
        password = "Password123!",
        tipoDocumento = "CC",
        numeroDocumento = "1000000001",
        fechaNacimiento = "1999-01-01",
        celular = "3001234567",
        selfieBase64 = "/9j/2Q=="
    )

    @Before
    fun iniciar() {
        Dispatchers.setMain(UnconfinedTestDispatcher())
        crear(BovedaFalsa())
    }

    @After
    fun terminar() {
        Dispatchers.resetMain()
    }

    private fun crear(nuevaBoveda: BovedaFalsa) {
        boveda = nuevaBoveda
        coordinador = AuthCoordinator(gateway, boveda, reloj) { true }
        viewModel = AuthViewModel(coordinador)
    }

    @Test
    fun elEstadoInicialEsElDelCoordinador() {
        crear(BovedaFalsa(guardado = "refresh-1"))

        assertTrue(viewModel.estado.value.biometriaActivada)
        assertNull(viewModel.estado.value.sesion)
    }

    @Test
    fun ingresarConCredencialesActualizaElEstado() {
        viewModel.ingresarConCredenciales("ana@gmail.com", "x")

        assertEquals(PERFIL_ANA, viewModel.estado.value.sesion?.perfil)
        assertTrue(viewModel.estado.value.ofrecerActivarBiometria)
    }

    @Test
    fun registrarMarcaElRegistroYSePuedeConsumir() {
        gateway.respuestaRegistro = ResultadoApi.Exito(RegistroCreado("ana@gmail.com", true))

        viewModel.registrar(datosRegistro)
        assertTrue(viewModel.estado.value.registroCompletado)

        viewModel.consumirRegistroCompletado()
        assertFalse(viewModel.estado.value.registroCompletado)
    }

    @Test
    fun activacionDeLaHuellaGuardaElRefreshToken() {
        viewModel.ingresarConCredenciales("ana@gmail.com", "x")
        viewModel.descartarActivacion()
        assertFalse(viewModel.estado.value.ofrecerActivarBiometria)

        viewModel.solicitarActivacion()
        assertTrue(viewModel.estado.value.ofrecerActivarBiometria)

        viewModel.prepararActivacion()
        viewModel.activarBiometria()

        assertEquals("refresh-1", boveda.guardado)
        assertTrue(viewModel.estado.value.biometriaActivada)
    }

    @Test
    fun ingresoBiometricoAbreSesion() {
        crear(BovedaFalsa(guardado = "refresh-1"))

        assertTrue(viewModel.solicitarIngresoBiometrico())
        viewModel.ingresarConBiometria()

        assertEquals(PERFIL_ANA, viewModel.estado.value.sesion?.perfil)
        assertEquals("refresh-2", boveda.guardado)
    }

    @Test
    fun sinHuellaGuardadaPideCredencialesYElEventoSeConsume() {
        assertFalse(viewModel.solicitarIngresoBiometrico())
        assertTrue(viewModel.estado.value.requiereCredenciales)

        viewModel.credencialesMostradas()

        assertFalse(viewModel.estado.value.requiereCredenciales)
    }

    @Test
    fun fallosDeLaHuellaMuestranMensajesQueSePuedenConsumir() {
        viewModel.huellaNoReconocida()
        assertEquals(MensajesAuth.HUELLA_NO_RECONOCIDA, viewModel.estado.value.mensaje)

        viewModel.falloBiometrico(FalloBiometrico.Bloqueado)
        assertEquals(MensajesAuth.BIOMETRIA_BLOQUEADA, viewModel.estado.value.mensaje)

        viewModel.consumirMensaje()
        assertNull(viewModel.estado.value.mensaje)
    }

    @Test
    fun descartarActivacionPuedeMostrarUnMensaje() {
        viewModel.descartarActivacion("Mensaje")

        assertEquals("Mensaje", viewModel.estado.value.mensaje)
    }

    @Test
    fun verificarExpiracionYRefrescarPerfilDelegan() {
        viewModel.ingresarConCredenciales("ana@gmail.com", "x")
        assertFalse(viewModel.verificarExpiracion())

        gateway.respuestaPerfil = ResultadoApi.Exito(PERFIL_ANA.copy(nombre = "Ana María"))
        viewModel.refrescarPerfil()
        assertEquals("Ana María", viewModel.estado.value.sesion?.perfil?.nombre)

        reloj.ahora += 1_800_000
        assertTrue(viewModel.verificarExpiracion())
        assertNull(viewModel.estado.value.sesion)
    }

    @Test
    fun cerrarSesionLimpiaLaSesion() {
        viewModel.ingresarConCredenciales("ana@gmail.com", "x")

        viewModel.cerrarSesion()

        assertNull(viewModel.estado.value.sesion)
        assertEquals(MensajesAuth.SESION_CERRADA, viewModel.estado.value.mensaje)
    }

    @Test
    fun laFabricaCreaElViewModelYAlLimpiarloDejaDeObservar() {
        val store = ViewModelStore()
        val creado = ViewModelProvider(store, AuthViewModel.Fabrica { coordinador })[AuthViewModel::class.java]
        assertNotNull(creado)

        store.clear()
        coordinador.huellaNoReconocida()

        // El ViewModel ya no recibe cambios del coordinador después de limpiarse.
        assertNull(creado.estado.value.mensaje)
    }
}
