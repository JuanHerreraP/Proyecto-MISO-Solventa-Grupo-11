package com.example.solventa.domain.siniestros

import com.example.solventa.domain.auth.ResultadoApi
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** HU20: reglas de la lista de siniestros del cliente, sin Android. */
class SiniestrosCoordinatorTest {

    private fun coordinador(
        gateway: SiniestrosGatewayFalso = SiniestrosGatewayFalso(),
        sesion: SesionSiniestrosFalsa = SesionSiniestrosFalsa()
    ) = SiniestrosCoordinator(gateway, sesion) to gateway

    @Test
    fun cargarEnviaElTokenYGuardaLosSiniestros() = runBlocking {
        val gateway = SiniestrosGatewayFalso()
        gateway.respuesta = ResultadoApi.Exito(
            siniestrosDe(
                siniestro(id = "SIN-1", origen = OrigenSiniestro.AUTOMATICO),
                siniestro(id = "SIN-2", origen = OrigenSiniestro.MANUAL, eventoId = null)
            )
        )
        val coordinador = SiniestrosCoordinator(gateway, SesionSiniestrosFalsa(token = "access-9"))

        coordinador.cargar()

        val estado = coordinador.estado
        assertFalse(estado.cargando)
        assertNull(estado.error)
        assertEquals(listOf("SIN-1", "SIN-2"), estado.siniestros?.siniestros?.map { it.siniestroId })
        assertEquals(1, estado.siniestros?.automaticos)
        assertEquals(listOf("access-9"), gateway.tokensUsados)
    }

    @Test
    fun errorGenericoCuandoElBackendFalla() = runBlocking {
        val (coordinador, gateway) = coordinador()
        gateway.respuesta = ResultadoApi.Fallo(500, null, null)

        coordinador.cargar()

        assertEquals(MensajesSiniestros.ERROR_GENERICO, coordinador.estado.error)
        assertNull(coordinador.estado.siniestros)
    }

    @Test
    fun sinConexionMuestraElMensajeDeRed() = runBlocking {
        val (coordinador, gateway) = coordinador()
        gateway.respuesta = ResultadoApi.SinConexion

        coordinador.cargar()

        assertEquals(MensajesSiniestros.SIN_CONEXION, coordinador.estado.error)
    }

    @Test
    fun token401CierraLaSesion() = runBlocking {
        val gateway = SiniestrosGatewayFalso()
        gateway.respuesta = ResultadoApi.Fallo(401, "TOKEN_EXPIRED", "El token expiró.")
        val sesion = SesionSiniestrosFalsa(token = "viejo")
        val coordinador = SiniestrosCoordinator(gateway, sesion)

        coordinador.cargar()

        assertEquals(1, sesion.rechazos)
        assertNull(sesion.token)
        assertEquals(MensajesSiniestros.SESION_VENCIDA, coordinador.estado.mensaje)
        assertNull(coordinador.estado.siniestros)
    }

    @Test
    fun sinTokenNoLlamaAlGatewayYCierraSesion() = runBlocking {
        val gateway = SiniestrosGatewayFalso()
        val sesion = SesionSiniestrosFalsa(token = null)
        val coordinador = SiniestrosCoordinator(gateway, sesion)

        coordinador.cargar()

        assertTrue(gateway.tokensUsados.isEmpty())
        assertEquals(1, sesion.rechazos)
        assertEquals(MensajesSiniestros.SESION_VENCIDA, coordinador.estado.mensaje)
    }

    @Test
    fun limpiarRestableceElEstadoEIgnoraRespuestasViejas() = runBlocking {
        val gateway = SiniestrosGatewayFalso()
        val coordinador = SiniestrosCoordinator(gateway, SesionSiniestrosFalsa())
        coordinador.cargar()
        assertTrue(coordinador.estado.siniestros != null)

        coordinador.limpiar()

        assertEquals(EstadoSiniestros(), coordinador.estado)
    }

    @Test
    fun consumirMensajeLoBorra() = runBlocking {
        val gateway = SiniestrosGatewayFalso()
        gateway.respuesta = ResultadoApi.Fallo(401, null, null)
        val coordinador = SiniestrosCoordinator(gateway, SesionSiniestrosFalsa())
        coordinador.cargar()
        assertEquals(MensajesSiniestros.SESION_VENCIDA, coordinador.estado.mensaje)

        coordinador.consumirMensaje()

        assertNull(coordinador.estado.mensaje)
    }

    @Test
    fun observadorRecibeElEstadoActualAlSuscribirse() {
        val coordinador = SiniestrosCoordinator(SiniestrosGatewayFalso(), SesionSiniestrosFalsa())
        var recibido: EstadoSiniestros? = null
        coordinador.observador = { recibido = it }
        assertEquals(coordinador.estado, recibido)
    }

    // --- Registro manual ---------------------------------------------------------------

    @Test
    fun registrarExitosoEnviaLaSolicitudMarcaEventoYRecargaLaLista() = runBlocking {
        val gateway = SiniestrosGatewayFalso()
        gateway.respuestaRegistro = ResultadoApi.Exito(siniestro(id = "SIN-NUEVO"))
        gateway.respuesta = ResultadoApi.Exito(siniestrosDe(siniestro(id = "SIN-NUEVO")))
        val coordinador = SiniestrosCoordinator(gateway, SesionSiniestrosFalsa(token = "access-1"))

        coordinador.registrar(solicitud(polizaId = "POL-9"))

        assertFalse(coordinador.estado.registrando)
        assertNull(coordinador.estado.errorFormulario)
        assertTrue(coordinador.estado.registroExitoso)
        assertEquals("POL-9", gateway.solicitudes.single().polizaId)
        // Tras el éxito recarga: la lista ya refleja el nuevo siniestro.
        assertEquals(listOf("SIN-NUEVO"), coordinador.estado.siniestros?.siniestros?.map { it.siniestroId })
    }

    @Test
    fun registrarPolizaInexistenteMuestraErrorDeFormulario() = runBlocking {
        val gateway = SiniestrosGatewayFalso()
        gateway.respuestaRegistro = ResultadoApi.Fallo(404, "POLIZA_NO_ENCONTRADA", "No existe.")
        val coordinador = SiniestrosCoordinator(gateway, SesionSiniestrosFalsa())

        coordinador.registrar(solicitud())

        assertEquals(MensajesSiniestros.POLIZA_NO_ENCONTRADA, coordinador.estado.errorFormulario)
        assertFalse(coordinador.estado.registroExitoso)
    }

    @Test
    fun registrarPolizaNoVigenteDa409() = runBlocking {
        val gateway = SiniestrosGatewayFalso()
        gateway.respuestaRegistro = ResultadoApi.Fallo(409, "POLIZA_NO_VIGENTE", "Vencida.")
        val coordinador = SiniestrosCoordinator(gateway, SesionSiniestrosFalsa())

        coordinador.registrar(solicitud())

        assertEquals(MensajesSiniestros.POLIZA_NO_VIGENTE, coordinador.estado.errorFormulario)
    }

    @Test
    fun registrarDatosInvalidosDa422() = runBlocking {
        val gateway = SiniestrosGatewayFalso()
        gateway.respuestaRegistro = ResultadoApi.Fallo(422, "FECHA_FUTURA", "Fecha futura.")
        val coordinador = SiniestrosCoordinator(gateway, SesionSiniestrosFalsa())

        coordinador.registrar(solicitud())

        assertEquals(MensajesSiniestros.DATOS_INVALIDOS, coordinador.estado.errorFormulario)
    }

    @Test
    fun registrar401CierraLaSesion() = runBlocking {
        val gateway = SiniestrosGatewayFalso()
        gateway.respuestaRegistro = ResultadoApi.Fallo(401, "TOKEN_EXPIRED", "Expiró.")
        val sesion = SesionSiniestrosFalsa(token = "viejo")
        val coordinador = SiniestrosCoordinator(gateway, sesion)

        coordinador.registrar(solicitud())

        assertEquals(1, sesion.rechazos)
        assertEquals(MensajesSiniestros.SESION_VENCIDA, coordinador.estado.mensaje)
        assertFalse(coordinador.estado.registroExitoso)
    }

    @Test
    fun registrarSinConexionMuestraMensajeDeRedEnElFormulario() = runBlocking {
        val gateway = SiniestrosGatewayFalso()
        gateway.respuestaRegistro = ResultadoApi.SinConexion
        val coordinador = SiniestrosCoordinator(gateway, SesionSiniestrosFalsa())

        coordinador.registrar(solicitud())

        assertEquals(MensajesSiniestros.SIN_CONEXION, coordinador.estado.errorFormulario)
    }

    @Test
    fun consumirRegistroExitosoLoApaga() = runBlocking {
        val gateway = SiniestrosGatewayFalso()
        val coordinador = SiniestrosCoordinator(gateway, SesionSiniestrosFalsa())
        coordinador.registrar(solicitud())
        assertTrue(coordinador.estado.registroExitoso)

        coordinador.consumirRegistroExitoso()

        assertFalse(coordinador.estado.registroExitoso)
    }
}
