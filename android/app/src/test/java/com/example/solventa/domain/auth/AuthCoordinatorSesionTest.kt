package com.example.solventa.domain.auth

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** HU07: la billetera obtiene el access token del coordinador, nunca de la UI. */
class AuthCoordinatorSesionTest {
    private val gateway = GatewayFalso()
    private val reloj = RelojFalso()
    private val auth = AuthCoordinator(gateway, BovedaFalsa(), reloj) { false }

    @Test
    fun sinSesionNoHayToken() {
        assertNull(auth.accessTokenVigente())
    }

    @Test
    fun conSesionEntregaElAccessTokenVigente() {
        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "clave") }

        assertEquals("access-1", auth.accessTokenVigente())
    }

    @Test
    fun unTokenVencidoNoSeEntregaYCierraLaSesion() {
        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "clave") }
        reloj.ahora += 1800 * 1000

        assertNull(auth.accessTokenVigente())
        assertNull(auth.estado.sesion)
        assertEquals(MensajesAuth.SESION_EXPIRADA, auth.estado.mensaje)
    }

    @Test
    fun siElBackendRechazaElTokenSeCierraLaSesion() {
        ejecutar { auth.ingresarConCredenciales("ana@gmail.com", "clave") }

        auth.sesionRechazada()

        assertNull(auth.estado.sesion)
        assertNull(auth.accessTokenVigente())
        assertEquals(MensajesAuth.SESION_EXPIRADA, auth.estado.mensaje)
    }

    @Test
    fun rechazarSinSesionNoCambiaNada() {
        val antes = auth.estado

        auth.sesionRechazada()

        assertEquals(antes, auth.estado)
    }
}
