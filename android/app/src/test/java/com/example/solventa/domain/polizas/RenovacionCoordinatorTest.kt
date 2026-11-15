package com.example.solventa.domain.polizas

import com.example.solventa.domain.auth.RelojFalso
import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.auth.ejecutar
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

/** HU22 (BPM-35): renovación de la póliza desde la billetera, sin Android. */
class RenovacionCoordinatorTest {
    private val gateway = PolizasGatewayFalso()
    private val sesion = SesionFalsa()
    private val billetera = BilleteraCoordinator(gateway, sesion, CachePolizasFalsa(), RelojFalso())

    @Test
    fun cargaLaPropuestaConElTokenDeLaSesion() {
        ejecutar { billetera.verPropuestaRenovacion("POL-1") }

        assertEquals(propuestaRenovacion(), billetera.estado.propuestaRenovacion)
        assertEquals(listOf("access-1"), gateway.tokensUsados)
        assertFalse(billetera.estado.cargandoRenovacion)
        assertNull(billetera.estado.errorRenovacion)
    }

    @Test
    fun conFalloMuestraUnMensajeYPermiteReintentar() {
        gateway.respuestaPropuestaRenovacion = ResultadoApi.Fallo(500, null, null)
        ejecutar { billetera.verPropuestaRenovacion("POL-1") }
        assertEquals(MensajesBilletera.RENOVACION_NO_DISPONIBLE, billetera.estado.errorRenovacion)

        gateway.respuestaPropuestaRenovacion = ResultadoApi.SinConexion
        ejecutar { billetera.verPropuestaRenovacion("POL-1") }
        assertEquals(MensajesBilletera.SIN_CONEXION, billetera.estado.errorRenovacion)

        gateway.respuestaPropuestaRenovacion = ResultadoApi.Exito(propuestaRenovacion())
        ejecutar { billetera.verPropuestaRenovacion("POL-1") }
        assertNull(billetera.estado.errorRenovacion)
        assertNotNull(billetera.estado.propuestaRenovacion)
    }

    @Test
    fun unaPolizaAjenaSeTrataComoNoEncontrada() {
        gateway.respuestaPropuestaRenovacion = ResultadoApi.Fallo(404, null, null)

        ejecutar { billetera.verPropuestaRenovacion("POL-1") }

        assertEquals(MensajesBilletera.POLIZA_NO_ENCONTRADA, billetera.estado.errorRenovacion)
        assertNull(billetera.estado.propuestaRenovacion)
    }

    @Test
    fun confirmarCreaLaRenovacionYDejaListoElPago() {
        ejecutar { billetera.iniciarRenovacion("POL-1") }

        assertEquals(listOf("POL-1"), gateway.renovacionesIniciadas)
        assertEquals(renovacionEnCurso(), billetera.estado.renovacionParaPagar)
        assertEquals(renovacionEnCurso(), billetera.estado.renovacionEnCurso)
        assertFalse(billetera.estado.iniciandoRenovacion)

        billetera.renovacionEnPago()

        assertNull(billetera.estado.renovacionParaPagar)
        // El pago aún necesita la cotización y el monto de la renovación.
        assertEquals(renovacionEnCurso(), billetera.estado.renovacionEnCurso)
    }

    @Test
    fun siNoSePuedeRenovarMuestraElMensajeDelBackend() {
        gateway.respuestaIniciarRenovacion =
            ResultadoApi.Fallo(409, "FUERA_DE_VENTANA", "Podrás renovar desde el 01/12/2026.")

        ejecutar { billetera.iniciarRenovacion("POL-1") }

        assertEquals("Podrás renovar desde el 01/12/2026.", billetera.estado.errorRenovacion)
        assertNull(billetera.estado.renovacionParaPagar)
    }

    @Test
    fun conFalloGenericoOSinConexionNoSeCreaNada() {
        gateway.respuestaIniciarRenovacion = ResultadoApi.Fallo(500, null, null)
        ejecutar { billetera.iniciarRenovacion("POL-1") }
        assertEquals(MensajesBilletera.RENOVACION_NO_INICIADA, billetera.estado.errorRenovacion)

        gateway.respuestaIniciarRenovacion = ResultadoApi.SinConexion
        ejecutar { billetera.iniciarRenovacion("POL-1") }
        assertEquals(MensajesBilletera.SIN_CONEXION, billetera.estado.errorRenovacion)
        assertNull(billetera.estado.renovacionParaPagar)
    }

    @Test
    fun unTokenRechazadoCierraLaSesion() {
        gateway.respuestaPropuestaRenovacion = ResultadoApi.Fallo(401, null, null)

        ejecutar { billetera.verPropuestaRenovacion("POL-1") }

        assertEquals(1, sesion.rechazos)
        assertNull(billetera.estado.propuestaRenovacion)
    }

    @Test
    fun cerrarLaPantallaDescartaLaPropuesta() {
        ejecutar { billetera.verPropuestaRenovacion("POL-1") }

        billetera.cerrarRenovacion()

        assertNull(billetera.estado.propuestaRenovacion)
        assertNull(billetera.estado.errorRenovacion)
    }

    @Test
    fun cerrarLaPantallaDeRenovarConservaLaRenovacionQueSePaga() {
        ejecutar { billetera.iniciarRenovacion("POL-1") }

        // Al avanzar al pago la pantalla de renovar sale de la composición y se cierra.
        billetera.cerrarRenovacion()
        assertEquals(renovacionEnCurso(), billetera.estado.renovacionEnCurso)

        billetera.terminarRenovacion()
        assertNull(billetera.estado.renovacionEnCurso)
    }

    @Test
    fun cargaLasCondicionesDeLaCancelacion() {
        ejecutar { billetera.verPropuestaCancelacion("POL-1") }

        assertEquals(propuestaCancelacion(), billetera.estado.propuestaCancelacion)
        assertNull(billetera.estado.errorCancelacion)
    }

    @Test
    fun cancelarEnviaElMotivoYMarcaLaPolizaComoCancelada() {
        ejecutar { billetera.cancelarPoliza("POL-1", "PRECIO_ALTO") }

        assertEquals(listOf("POL-1" to "PRECIO_ALTO"), gateway.cancelaciones)
        assertEquals(cancelacionRealizada(), billetera.estado.cancelacionRealizada)
        assertFalse(billetera.estado.cancelando)

        billetera.cerrarCancelacion()
        assertNull(billetera.estado.cancelacionRealizada)
    }

    @Test
    fun unSiniestroEnTramiteMuestraElMensajeDelBackend() {
        gateway.respuestaCancelar =
            ResultadoApi.Fallo(409, "SINIESTRO_EN_TRAMITE", "Tienes un siniestro en trámite.")

        ejecutar { billetera.cancelarPoliza("POL-1", "OTRO") }

        assertEquals("Tienes un siniestro en trámite.", billetera.estado.errorCancelacion)
        assertNull(billetera.estado.cancelacionRealizada)
    }

    @Test
    fun conFalloGenericoOSinConexionNoSeCancelaNada() {
        gateway.respuestaCancelar = ResultadoApi.Fallo(500, null, null)
        ejecutar { billetera.cancelarPoliza("POL-1", "OTRO") }
        assertEquals(MensajesBilletera.CANCELACION_FALLIDA, billetera.estado.errorCancelacion)

        gateway.respuestaCancelar = ResultadoApi.SinConexion
        ejecutar { billetera.cancelarPoliza("POL-1", "OTRO") }
        assertEquals(MensajesBilletera.SIN_CONEXION, billetera.estado.errorCancelacion)
        assertNull(billetera.estado.cancelacionRealizada)
    }

    @Test
    fun unTokenRechazadoAlCancelarCierraLaSesion() {
        gateway.respuestaCancelar = ResultadoApi.Fallo(401, null, null)

        ejecutar { billetera.cancelarPoliza("POL-1", "OTRO") }

        assertEquals(1, sesion.rechazos)
        assertNull(billetera.estado.cancelacionRealizada)
    }
}
