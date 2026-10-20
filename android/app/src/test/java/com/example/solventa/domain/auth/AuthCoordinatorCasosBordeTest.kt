package com.example.solventa.domain.auth

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Ramas del [AuthCoordinator] que no cubre el flujo principal de [AuthCoordinatorTest]. */
class AuthCoordinatorCasosBordeTest {
    private val gateway = GatewayFalso()
    private val reloj = RelojFalso()

    private fun coordinador(
        boveda: BovedaSesion = BovedaFalsa(),
        biometriaDisponible: Boolean = true
    ) = AuthCoordinator(gateway, boveda, reloj) { biometriaDisponible }

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

    // --- Registro ---

    @Test
    fun registroSinConexionSeInforma() {
        gateway.respuestaRegistro = ResultadoApi.SinConexion
        val auth = coordinador()

        ejecutar { auth.registrar(datosRegistro) }

        assertEquals(MensajesAuth.SIN_CONEXION, auth.estado.mensaje)
        assertFalse(auth.estado.cargando)
    }

    @Test
    fun registroFallidoSinMensajeMuestraErrorGenerico() {
        gateway.respuestaRegistro = ResultadoApi.Fallo(500, null, null)
        val auth = coordinador()

        ejecutar { auth.registrar(datosRegistro) }

        assertEquals(MensajesAuth.ERROR_GENERICO, auth.estado.mensaje)
    }

    @Test
    fun consumirRegistroCompletadoSoloCambiaSiEstabaMarcado() {
        val auth = coordinador()
        val antes = auth.estado
        auth.consumirRegistroCompletado()
        assertEquals(antes, auth.estado)

        ejecutar { auth.registrar(datosRegistro) }
        auth.consumirRegistroCompletado()

        assertFalse(auth.estado.registroCompletado)
    }

    // --- Credenciales y perfil ---

    @Test
    fun errorDelServidorSinMensajeAlIngresarMuestraErrorGenerico() {
        gateway.respuestaLogin = ResultadoApi.Fallo(500, null, null)
        val auth = coordinador()

        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        assertEquals(MensajesAuth.ERROR_GENERICO, auth.estado.mensaje)
    }

    @Test
    fun siFallaElPerfilLaSesionNoSeAbre() {
        gateway.respuestaPerfil = ResultadoApi.Fallo(500, null, "Perfil no disponible")
        val auth = coordinador()

        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        assertNull(auth.estado.sesion)
        assertEquals("Perfil no disponible", auth.estado.mensaje)
    }

    @Test
    fun siFallaElPerfilSinMensajeSeMuestraErrorGenerico() {
        gateway.respuestaPerfil = ResultadoApi.Fallo(500, null, null)
        val auth = coordinador()

        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        assertEquals(MensajesAuth.ERROR_GENERICO, auth.estado.mensaje)
    }

    @Test
    fun sinConexionAlPedirElPerfilLaSesionNoSeAbre() {
        gateway.respuestaPerfil = ResultadoApi.SinConexion
        val auth = coordinador()

        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        assertNull(auth.estado.sesion)
        assertEquals(MensajesAuth.SIN_CONEXION, auth.estado.mensaje)
    }

    @Test
    fun refrescarPerfilActualizaLosDatos() {
        val auth = coordinador()
        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }
        gateway.respuestaPerfil = ResultadoApi.Exito(PERFIL_ANA.copy(apellido = "Gómez"))

        ejecutar { auth.refrescarPerfil() }

        assertEquals("Gómez", auth.estado.sesion?.perfil?.apellido)
    }

    @Test
    fun refrescarPerfilSinConexionOConOtroErrorConservaLaSesion() {
        val auth = coordinador()
        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        gateway.respuestaPerfil = ResultadoApi.SinConexion
        ejecutar { auth.refrescarPerfil() }
        assertEquals(PERFIL_ANA, auth.estado.sesion?.perfil)

        gateway.respuestaPerfil = ResultadoApi.Fallo(500, null, null)
        ejecutar { auth.refrescarPerfil() }
        assertEquals(PERFIL_ANA, auth.estado.sesion?.perfil)
    }

    @Test
    fun refrescarPerfilSinSesionNoLlamaAlBackend() {
        val auth = coordinador()

        ejecutar { auth.refrescarPerfil() }

        assertTrue(gateway.perfilesPedidos.isEmpty())
    }

    @Test
    fun verificarExpiracionSinSesionDevuelveFalso() {
        assertFalse(coordinador().verificarExpiracion())
    }

    // --- Ingreso biométrico ---

    @Test
    fun usuarioInactivoAlRenovarBorraLaBovedaConElMensajeDelServidor() {
        gateway.respuestaRenovar = ResultadoApi.Fallo(403, "USER_INACTIVE", "Usuario inactivo")
        val boveda = BovedaFalsa(guardado = "refresh-1")
        val auth = coordinador(boveda)

        ejecutar { auth.ingresarConBiometria() }

        assertNull(boveda.guardado)
        assertTrue(auth.estado.requiereCredenciales)
        assertEquals("Usuario inactivo", auth.estado.mensaje)
    }

    @Test
    fun rechazo403SinMensajeUsaElMensajeDeSesionInvalida() {
        gateway.respuestaRenovar = ResultadoApi.Fallo(403, null, null)
        val auth = coordinador(BovedaFalsa(guardado = "refresh-1"))

        ejecutar { auth.ingresarConBiometria() }

        assertEquals(MensajesAuth.SESION_GUARDADA_INVALIDA, auth.estado.mensaje)
    }

    @Test
    fun errorDelServidorAlRenovarConservaLaBoveda() {
        val boveda = BovedaFalsa(guardado = "refresh-1")
        val auth = coordinador(boveda)

        gateway.respuestaRenovar = ResultadoApi.Fallo(500, null, "Servidor caído")
        ejecutar { auth.ingresarConBiometria() }
        assertEquals("Servidor caído", auth.estado.mensaje)

        gateway.respuestaRenovar = ResultadoApi.Fallo(500, null, null)
        ejecutar { auth.ingresarConBiometria() }
        assertEquals(MensajesAuth.ERROR_GENERICO, auth.estado.mensaje)

        assertEquals("refresh-1", boveda.guardado)
        assertNull(auth.estado.sesion)
    }

    // --- Activación ---

    @Test
    fun prepararActivacionCreaLaLlave() {
        val boveda = BovedaFalsa()
        val auth = coordinador(boveda)

        auth.prepararActivacion()

        assertTrue(boveda.preparada)
    }

    @Test
    fun siNoSePuedePrepararLaLlaveSeCancelaLaActivacion() {
        val boveda = object : BovedaSesion by BovedaFalsa() {
            override fun preparar() {
                throw IllegalStateException("sin keystore")
            }
        }
        val auth = coordinador(boveda)
        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "x") }

        auth.prepararActivacion()

        assertFalse(auth.estado.ofrecerActivarBiometria)
        assertEquals(MensajesAuth.ACTIVACION_FALLIDA, auth.estado.mensaje)
    }

    @Test
    fun activarSinSesionNoHaceNada() {
        val boveda = BovedaFalsa()
        val auth = coordinador(boveda)

        auth.activarBiometria()

        assertNull(boveda.guardado)
        assertFalse(auth.estado.biometriaActivada)
    }

    @Test
    fun conHuellaYaActivadaNoSeVuelveAOfrecer() {
        val auth = coordinador(BovedaFalsa(guardado = "refresh-1"))
        ejecutar { auth.ingresarConBiometria() }

        auth.solicitarActivacion()

        assertFalse(auth.estado.ofrecerActivarBiometria)
    }

    // --- Mensajes y eventos ---

    @Test
    fun consumirMensajeSinMensajeNoCambiaElEstado() {
        val auth = coordinador()
        val antes = auth.estado

        auth.consumirMensaje()
        auth.credencialesMostradas()

        assertEquals(antes, auth.estado)
    }

    @Test
    fun cerrarSesionSinSesionAbiertaNoLlamaAlBackend() {
        val auth = coordinador()

        ejecutar { auth.cerrarSesion() }

        assertTrue(gateway.cerrados.isEmpty())
        assertEquals(MensajesAuth.SESION_CERRADA, auth.estado.mensaje)
    }

    // --- Modelos ---

    @Test
    fun mapearTransformaSoloLosResultadosExitosos() {
        val exito: ResultadoApi<Int> = ResultadoApi.Exito(1)
        val fallo: ResultadoApi<Int> = ResultadoApi.Fallo(400, "X", "Y")
        val sinConexion: ResultadoApi<Int> = ResultadoApi.SinConexion

        assertEquals(ResultadoApi.Exito(2), exito.mapear { it + 1 })
        assertEquals(fallo, fallo.mapear { it + 1 })
        assertEquals(ResultadoApi.SinConexion, sinConexion.mapear { it + 1 })
    }

    @Test
    fun lasExcepcionesDeLaBovedaConservanLaCausa() {
        val causa = RuntimeException("causa")

        assertEquals(causa, LlaveInvalidadaException(causa).cause)
        assertEquals(causa, AutenticacionVencidaException(causa).cause)
        assertNull(LlaveInvalidadaException().cause)
    }
}
