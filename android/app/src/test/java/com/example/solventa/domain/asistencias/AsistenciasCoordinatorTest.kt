package com.example.solventa.domain.asistencias

import com.example.solventa.domain.auth.ResultadoApi
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AsistenciasCoordinatorTest {

    private fun coordinador(
        gateway: AsistenciasGatewayFalso = AsistenciasGatewayFalso(),
        sesion: SesionAsistenciasFalsa = SesionAsistenciasFalsa()
    ) = AsistenciasCoordinator(gateway, sesion) to gateway

    /** Avanza hasta tener póliza y servicio elegidos (precondición para buscar y solicitar). */
    private suspend fun AsistenciasCoordinator.conPolizaYServicio() {
        seleccionarPoliza("POL-1", "Protección de dispositivos · SOL-DP-1")
        seleccionarServicio(servicioAsistencia())
    }

    @Test
    fun seleccionarPolizaCargaLosServicios() = runBlocking {
        val (coord, gateway) = coordinador()
        coord.seleccionarPoliza("POL-1", "Protección de dispositivos · SOL-DP-1")

        assertEquals(PasoAsistencia.SELECCION_SERVICIO, coord.estado.paso)
        assertEquals(2, coord.estado.servicios.size)
        assertEquals("POL-1", coord.estado.polizaSeleccionadaId)
        assertTrue(gateway.tokensUsados.contains("access-1"))
    }

    @Test
    fun servicioSinConexionMuestraMensaje() = runBlocking {
        val gateway = AsistenciasGatewayFalso().apply { respuestaServicios = ResultadoApi.SinConexion }
        val (coord, _) = coordinador(gateway)
        coord.seleccionarPoliza("POL-1", "x")
        assertEquals(MensajesAsistencias.SIN_CONEXION, coord.estado.error)
    }

    @Test
    fun seleccionarServicioAvanzaAPermiso() {
        val (coord, _) = coordinador()
        coord.seleccionarServicio(servicioAsistencia())
        assertEquals(PasoAsistencia.PERMISO_UBICACION, coord.estado.paso)
        assertEquals(TipoServicio.REPARACION_DISPOSITIVO, coord.estado.servicioSeleccionado?.codigo)
    }

    @Test
    fun buscarSinUbicacionPideElPermisoDeNuevo() = runBlocking {
        val (coord, _) = coordinador()
        coord.conPolizaYServicio()
        coord.buscarPrestadores(ubicacion = null)
        assertTrue(coord.estado.permisoDenegado)
        assertEquals(MensajesAsistencias.UBICACION_NO_DISPONIBLE, coord.estado.error)
    }

    @Test
    fun buscarConUbicacionTraeLosPrestadoresEnElOrdenRecibido() = runBlocking {
        val (coord, _) = coordinador()
        coord.conPolizaYServicio()
        coord.buscarPrestadores(BOGOTA, radioKm = 25.0)

        assertEquals(PasoAsistencia.PRESTADORES, coord.estado.paso)
        assertEquals(
            listOf("PREST-TEC-001", "PREST-TEC-002"),
            coord.estado.prestadores.map { it.prestadorId }
        )
    }

    @Test
    fun buscarConRadioAmpliadoLoReenviaAlGateway() = runBlocking {
        val (coord, gateway) = coordinador()
        coord.conPolizaYServicio()
        coord.buscarPrestadores(BOGOTA, radioKm = 50.0)
        assertEquals(50.0, gateway.ultimoRadioKm!!, 0.0)
    }

    @Test
    fun solicitarCreaLaAsistenciaYMarcaExito() = runBlocking {
        val (coord, gateway) = coordinador()
        coord.conPolizaYServicio()
        coord.buscarPrestadores(BOGOTA)
        coord.seleccionarPrestador(prestadorCercano())
        coord.solicitar("El dispositivo no enciende.")

        assertEquals(PasoAsistencia.EXITO, coord.estado.paso)
        assertFalse(coord.estado.solicitando)
        assertEquals("ASI-1", coord.estado.asistenciaCreada?.asistenciaId)
        // El cliente nunca va en la solicitud; sí van póliza, prestador, servicio y ubicación.
        val enviada = gateway.solicitudes.single()
        assertEquals("POL-1", enviada.polizaId)
        assertEquals("PREST-TEC-001", enviada.prestadorId)
        assertEquals("El dispositivo no enciende.", enviada.observaciones)
    }

    @Test
    fun solicitarConPrestadorNoDisponibleMuestraMensaje() = runBlocking {
        val gateway = AsistenciasGatewayFalso().apply {
            respuestaSolicitar = ResultadoApi.Fallo(409, "PRESTADOR_NO_DISPONIBLE", null)
        }
        val (coord, _) = coordinador(gateway)
        coord.conPolizaYServicio()
        coord.buscarPrestadores(BOGOTA)
        coord.seleccionarPrestador(prestadorCercano())
        coord.solicitar(null)
        assertEquals(MensajesAsistencias.PRESTADOR_NO_DISPONIBLE, coord.estado.error)
        assertFalse(coord.estado.solicitando)
    }

    @Test
    fun cargarAsistenciasListaLasDelCliente() = runBlocking {
        val (coord, _) = coordinador()
        coord.cargarAsistencias()
        assertEquals(PasoAsistencia.MIS_ASISTENCIAS, coord.estado.paso)
        assertEquals(1, coord.estado.asistencias.size)
    }

    @Test
    fun cancelarActualizaElEstadoEnLaLista() = runBlocking {
        val gateway = AsistenciasGatewayFalso()
        val (coord, _) = coordinador(gateway)
        coord.cargarAsistencias()
        coord.cancelar("ASI-1")
        assertEquals(EstadoAsistencia.CANCELADA, coord.estado.asistencias.single().estado)
        assertEquals(listOf("ASI-1"), gateway.canceladas)
        assertNull(coord.estado.cancelandoId)
    }

    @Test
    fun cancelarYaCanceladaMuestraMensaje() = runBlocking {
        val gateway = AsistenciasGatewayFalso().apply {
            respuestaCancelar = ResultadoApi.Fallo(409, "ASISTENCIA_YA_CANCELADA", null)
        }
        val (coord, _) = coordinador(gateway)
        coord.cargarAsistencias()
        coord.cancelar("ASI-1")
        assertEquals(MensajesAsistencias.ASISTENCIA_YA_CANCELADA, coord.estado.error)
    }

    @Test
    fun tokenRechazadoCierraLaSesion() = runBlocking {
        val gateway = AsistenciasGatewayFalso().apply {
            respuestaServicios = ResultadoApi.Fallo(401, "TOKEN_EXPIRED", null)
        }
        val sesion = SesionAsistenciasFalsa()
        val coord = AsistenciasCoordinator(gateway, sesion)
        coord.seleccionarPoliza("POL-1", "x")
        assertEquals(1, sesion.rechazos)
        assertEquals(MensajesAsistencias.SESION_VENCIDA, coord.estado.aviso)
    }

    @Test
    fun sinTokenNoLlamaAlGatewayYCierraSesion() = runBlocking {
        val gateway = AsistenciasGatewayFalso()
        val sesion = SesionAsistenciasFalsa(token = null)
        val coord = AsistenciasCoordinator(gateway, sesion)
        coord.seleccionarPoliza("POL-1", "x")
        assertTrue(gateway.tokensUsados.isEmpty())
        assertEquals(1, sesion.rechazos)
    }

    @Test
    fun limpiarVuelveAlEstadoInicial() = runBlocking {
        val (coord, _) = coordinador()
        coord.cargarAsistencias()
        coord.limpiar()
        assertEquals(EstadoAsistencias(), coord.estado)
    }

    @Test
    fun reiniciarFlujoVuelveASeleccionDePoliza() = runBlocking {
        val (coord, _) = coordinador()
        coord.cargarAsistencias()
        coord.reiniciarFlujo()
        assertEquals(PasoAsistencia.SELECCION_POLIZA, coord.estado.paso)
    }
}
