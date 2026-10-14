package com.example.solventa.domain.auth

import com.example.solventa.biometric.FalloBiometrico
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** HU02 (BPM-23): pruebas del flujo biométrico, el fallback y la sesión (BPM-119). */
class AuthCoordinatorTest {
    private val gateway = GatewayFalso()
    private val reloj = RelojFalso()

    private fun coordinador(
        boveda: BovedaSesion = BovedaFalsa(),
        biometriaDisponible: Boolean = true
    ) = AuthCoordinator(gateway, boveda, reloj) { biometriaDisponible }

    // --- Ingreso con credenciales (fallback) ---

    @Test
    fun ingresoConCredencialesAbreSesionConElPerfilDelUsuario() {
        val auth = coordinador()

        ejecutar { auth.ingresarConCredenciales(" ana@gmail.com ", "Password123!") }

        assertEquals(PERFIL_ANA, auth.estado.sesion?.perfil)
        assertEquals(listOf("access-1"), gateway.perfilesPedidos)
        assertFalse(auth.estado.cargando)
        assertNull(auth.estado.mensaje)
    }

    @Test
    fun ingresoConCredencialesOfreceActivarLaHuellaSiHayBiometria() {
        val auth = coordinador(biometriaDisponible = true)

        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        assertTrue(auth.estado.ofrecerActivarBiometria)
    }

    @Test
    fun sinBiometriaNoSeOfreceActivarla() {
        val auth = coordinador(biometriaDisponible = false)

        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        assertFalse(auth.estado.ofrecerActivarBiometria)
    }

    @Test
    fun credencialesInvalidasNoAbrenSesionNiMuestranDatos() {
        gateway.respuestaLogin = ResultadoApi.Fallo(401, "INVALID_CREDENTIALS", "mensaje del servidor")
        val auth = coordinador()

        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "mala") }

        assertNull(auth.estado.sesion)
        assertEquals(MensajesAuth.CREDENCIALES_INVALIDAS, auth.estado.mensaje)
        assertTrue(gateway.perfilesPedidos.isEmpty())
    }

    @Test
    fun usuarioInactivoMuestraElMensajeDelServidor() {
        gateway.respuestaLogin = ResultadoApi.Fallo(403, "USER_INACTIVE", "El usuario se encuentra inactivo.")
        val auth = coordinador()

        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        assertEquals("El usuario se encuentra inactivo.", auth.estado.mensaje)
    }

    @Test
    fun sinConexionSeInformaSinAbrirSesion() {
        gateway.respuestaLogin = ResultadoApi.SinConexion
        val auth = coordinador()

        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        assertNull(auth.estado.sesion)
        assertEquals(MensajesAuth.SIN_CONEXION, auth.estado.mensaje)
    }

    @Test
    fun ingresoConCredencialesDescartaUnaBovedaAnterior() {
        val boveda = BovedaFalsa(guardado = "refresh-viejo")
        val auth = coordinador(boveda)

        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        assertNull(boveda.guardado)
        assertTrue(auth.estado.ofrecerActivarBiometria)
    }

    // --- Activación de la huella ---

    @Test
    fun activarBiometriaGuardaElRefreshTokenEnLaBoveda() {
        val boveda = BovedaFalsa()
        val auth = coordinador(boveda)
        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        auth.prepararActivacion()
        auth.activarBiometria()

        assertTrue(boveda.preparada)
        assertEquals("refresh-1", boveda.guardado)
        assertTrue(auth.estado.biometriaActivada)
        assertFalse(auth.estado.ofrecerActivarBiometria)
    }

    @Test
    fun siLaActivacionFallaLaBovedaQuedaVacia() {
        val boveda = BovedaFalsa().apply { errorAlGuardar = AutenticacionVencidaException() }
        val auth = coordinador(boveda)
        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        auth.activarBiometria()

        assertNull(boveda.guardado)
        assertFalse(auth.estado.biometriaActivada)
        assertEquals(MensajesAuth.ACTIVACION_FALLIDA, auth.estado.mensaje)
    }

    @Test
    fun descartarActivacionNoGuardaNada() {
        val boveda = BovedaFalsa()
        val auth = coordinador(boveda)
        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        auth.descartarActivacion()

        assertNull(boveda.guardado)
        assertFalse(auth.estado.ofrecerActivarBiometria)
    }

    @Test
    fun despuesDeAhoraNoSePuedeVolverAOfrecerLaActivacion() {
        val auth = coordinador(BovedaFalsa())
        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }
        auth.descartarActivacion()

        auth.solicitarActivacion()

        assertTrue(auth.estado.ofrecerActivarBiometria)
    }

    @Test
    fun sinSesionOSinBiometriaNoSeOfreceActivacion() {
        val sinSesion = coordinador(BovedaFalsa())
        sinSesion.solicitarActivacion()
        assertFalse(sinSesion.estado.ofrecerActivarBiometria)

        val sinBiometria = coordinador(BovedaFalsa(), biometriaDisponible = false)
        ejecutar { sinBiometria.ingresarConCredenciales("ana@gmail.com", "x") }
        sinBiometria.solicitarActivacion()
        assertFalse(sinBiometria.estado.ofrecerActivarBiometria)
    }

    // --- Ingreso biométrico ---

    @Test
    fun sinHuellaActivadaSeLlevaAlIngresoConCredenciales() {
        val auth = coordinador(BovedaFalsa())

        val mostrarDialogo = auth.solicitarIngresoBiometrico()

        assertFalse(mostrarDialogo)
        assertTrue(auth.estado.requiereCredenciales)
        assertEquals(MensajesAuth.BIOMETRIA_NO_ACTIVADA, auth.estado.mensaje)
    }

    @Test
    fun conHuellaActivadaSeMuestraElDialogoBiometrico() {
        val auth = coordinador(BovedaFalsa(guardado = "refresh-1"))

        assertTrue(auth.estado.biometriaActivada)
        assertTrue(auth.solicitarIngresoBiometrico())
    }

    @Test
    fun ingresoBiometricoRenuevaYGuardaElNuevoRefreshToken() {
        val boveda = BovedaFalsa(guardado = "refresh-1")
        val auth = coordinador(boveda)

        ejecutar { auth.ingresarConBiometria() }

        assertEquals(listOf("refresh-1"), gateway.renovados)
        assertEquals("refresh-2", boveda.guardado)
        assertEquals(PERFIL_ANA, auth.estado.sesion?.perfil)
        assertEquals(listOf("access-2"), gateway.perfilesPedidos)
        assertFalse(auth.estado.ofrecerActivarBiometria)
    }

    @Test
    fun refreshGuardadoRechazadoBorraLaBovedaYPideCredenciales() {
        gateway.respuestaRenovar = ResultadoApi.Fallo(401, "REFRESH_REUSED", "cerrada por seguridad")
        val boveda = BovedaFalsa(guardado = "refresh-1")
        val auth = coordinador(boveda)

        ejecutar { auth.ingresarConBiometria() }

        assertNull(boveda.guardado)
        assertNull(auth.estado.sesion)
        assertTrue(auth.estado.requiereCredenciales)
        assertFalse(auth.estado.biometriaActivada)
        assertEquals(MensajesAuth.SESION_GUARDADA_INVALIDA, auth.estado.mensaje)
    }

    @Test
    fun cambioEnLasHuellasInvalidaLaLlaveYPideCredenciales() {
        val boveda = BovedaFalsa(guardado = "refresh-1").apply { errorAlLeer = LlaveInvalidadaException() }
        val auth = coordinador(boveda)

        ejecutar { auth.ingresarConBiometria() }

        assertNull(boveda.guardado)
        assertTrue(auth.estado.requiereCredenciales)
        assertEquals(MensajesAuth.BIOMETRIA_CAMBIO, auth.estado.mensaje)
        assertTrue(gateway.renovados.isEmpty())
    }

    @Test
    fun autenticacionVencidaPermiteReintentarSinBorrarLaBoveda() {
        val boveda = BovedaFalsa(guardado = "refresh-1").apply { errorAlLeer = AutenticacionVencidaException() }
        val auth = coordinador(boveda)

        ejecutar { auth.ingresarConBiometria() }

        assertEquals("refresh-1", boveda.guardado)
        assertFalse(auth.estado.requiereCredenciales)
        assertEquals(MensajesAuth.REINTENTAR_BIOMETRIA, auth.estado.mensaje)
    }

    @Test
    fun sinConexionDuranteElIngresoBiometricoConservaLaBoveda() {
        gateway.respuestaRenovar = ResultadoApi.SinConexion
        val boveda = BovedaFalsa(guardado = "refresh-1")
        val auth = coordinador(boveda)

        ejecutar { auth.ingresarConBiometria() }

        assertEquals("refresh-1", boveda.guardado)
        assertNull(auth.estado.sesion)
        assertEquals(MensajesAuth.SIN_CONEXION, auth.estado.mensaje)
    }

    @Test
    fun siNoSePuedeGuardarElNuevoRefreshLaSesionAbrePeroLaHuellaQuedaDesactivada() {
        val boveda = BovedaFalsa(guardado = "refresh-1").apply { errorAlGuardar = AutenticacionVencidaException() }
        val auth = coordinador(boveda)

        ejecutar { auth.ingresarConBiometria() }

        assertEquals(PERFIL_ANA, auth.estado.sesion?.perfil)
        assertNull(boveda.guardado)
        assertFalse(auth.estado.biometriaActivada)
    }

    // --- Errores del diálogo biométrico ---

    @Test
    fun bloqueoPorIntentosLlevaAlIngresoConCredenciales() {
        val auth = coordinador(BovedaFalsa(guardado = "refresh-1"))

        auth.falloBiometrico(FalloBiometrico.Bloqueado)

        assertTrue(auth.estado.requiereCredenciales)
        assertEquals(MensajesAuth.BIOMETRIA_BLOQUEADA, auth.estado.mensaje)
    }

    @Test
    fun biometriaNoDisponibleLlevaAlIngresoConCredenciales() {
        val auth = coordinador(BovedaFalsa(guardado = "refresh-1"))

        auth.falloBiometrico(FalloBiometrico.NoDisponible)

        assertTrue(auth.estado.requiereCredenciales)
    }

    @Test
    fun cancelarNoCambiaDePantallaNiAbreSesion() {
        val auth = coordinador(BovedaFalsa(guardado = "refresh-1"))

        auth.falloBiometrico(FalloBiometrico.Cancelado)

        assertFalse(auth.estado.requiereCredenciales)
        assertNull(auth.estado.sesion)
    }

    @Test
    fun huellaNoReconocidaPermiteOtroIntento() {
        val auth = coordinador(BovedaFalsa(guardado = "refresh-1"))

        auth.huellaNoReconocida()

        assertNull(auth.estado.sesion)
        assertFalse(auth.estado.requiereCredenciales)
        assertEquals(MensajesAuth.HUELLA_NO_RECONOCIDA, auth.estado.mensaje)
    }

    @Test
    fun errorTransitorioMuestraElMensajeYPermiteReintentar() {
        val auth = coordinador(BovedaFalsa(guardado = "refresh-1"))

        auth.falloBiometrico(FalloBiometrico.Reintentable("Sensor ocupado"))

        assertEquals("Sensor ocupado", auth.estado.mensaje)
        assertFalse(auth.estado.requiereCredenciales)
    }

    @Test
    fun elEventoDeCredencialesSeConsume() {
        val auth = coordinador(BovedaFalsa())
        auth.solicitarIngresoBiometrico()

        auth.credencialesMostradas()

        assertFalse(auth.estado.requiereCredenciales)
    }

    // --- Expiración y cierre de sesión ---

    @Test
    fun laSesionExpiraCuandoVenceElAccessToken() {
        val auth = coordinador(BovedaFalsa())
        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        reloj.ahora += 1_799_000
        assertFalse(auth.verificarExpiracion())
        reloj.ahora += 1_000
        assertTrue(auth.verificarExpiracion())

        assertNull(auth.estado.sesion)
        assertEquals(MensajesAuth.SESION_EXPIRADA, auth.estado.mensaje)
    }

    @Test
    fun laExpiracionConservaLaHuellaParaVolverAEntrar() {
        val boveda = BovedaFalsa(guardado = "refresh-1")
        val auth = coordinador(boveda)
        ejecutar { auth.ingresarConBiometria() }

        auth.sesionExpirada()

        assertEquals("refresh-2", boveda.guardado)
        assertTrue(auth.estado.biometriaActivada)
    }

    @Test
    fun tokenRechazadoAlRefrescarElPerfilExpiraLaSesion() {
        val auth = coordinador()
        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }
        gateway.respuestaPerfil = ResultadoApi.Fallo(401, "TOKEN_EXPIRED", null)

        ejecutar { auth.refrescarPerfil() }

        assertNull(auth.estado.sesion)
    }

    @Test
    fun cerrarSesionRevocaEnElBackendYBorraLaBoveda() {
        val boveda = BovedaFalsa(guardado = "refresh-1")
        val auth = coordinador(boveda)
        ejecutar { auth.ingresarConBiometria() }

        ejecutar { auth.cerrarSesion() }

        assertEquals(listOf("refresh-2"), gateway.cerrados)
        assertNull(boveda.guardado)
        assertNull(auth.estado.sesion)
        assertFalse(auth.estado.biometriaActivada)
        assertEquals(MensajesAuth.SESION_CERRADA, auth.estado.mensaje)
    }

    @Test
    fun elObservadorRecibeElEstadoActualYLosCambios() {
        val auth = coordinador()
        val vistos = mutableListOf<EstadoAuth>()

        auth.observador = { vistos += it }
        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        assertNull(vistos.first().sesion)
        assertTrue(vistos.any { it.cargando })
        assertEquals(PERFIL_ANA, vistos.last().sesion?.perfil)
    }
}
