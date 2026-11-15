package com.example.solventa.data.remote

import com.example.solventa.domain.asistencias.EstadoAsistencia
import com.example.solventa.domain.asistencias.NuevaAsistencia
import com.example.solventa.domain.asistencias.TipoServicio
import com.example.solventa.domain.auth.ResultadoApi
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/** HU06: el gateway de asistencias contra un servidor HTTP falso, con Retrofit y Gson reales. */
class RemoteAsistenciasGatewayTest {
    private lateinit var servidor: MockWebServer
    private lateinit var gateway: RemoteAsistenciasGateway

    @Before
    fun iniciar() {
        servidor = MockWebServer()
        servidor.start()
        gateway = RemoteAsistenciasGateway(
            ApiClient.crearAsistenciasApi(servidor.url("/").toString())
        )
    }

    @After
    fun detener() {
        try {
            servidor.shutdown()
        } catch (ignorado: Exception) {
        }
    }

    private fun responder(codigo: Int, cuerpo: String = "") {
        servidor.enqueue(
            MockResponse().setResponseCode(codigo)
                .setHeader("Content-Type", "application/json")
                .setBody(cuerpo)
        )
    }

    @Test
    fun serviciosEnviaTokenYPolizaYMapea() = runBlocking {
        responder(
            200,
            """{"poliza_id":"POL-1","ramo":"PROTECCION_DISPOSITIVOS",
                "servicios":[{"codigo":"DIAGNOSTICO_TECNICO","nombre":"Diagnóstico técnico"},
                {"codigo":"REPARACION_DISPOSITIVO","nombre":"Reparación de dispositivo"}]}"""
        )

        val resultado = gateway.servicios("access-1", "POL-1")

        val servicios = (resultado as ResultadoApi.Exito).valor
        assertEquals(2, servicios.servicios.size)
        assertEquals(TipoServicio.DIAGNOSTICO_TECNICO, servicios.servicios[0].codigo)
        val peticion = servidor.takeRequest()
        assertEquals("GET", peticion.method)
        assertEquals("/api/v1/asistencias/servicios?poliza_id=POL-1", peticion.path)
        assertEquals("Bearer access-1", peticion.getHeader("Authorization"))
    }

    @Test
    fun serviciosVidaListaVacia() = runBlocking {
        responder(200, """{"poliza_id":"POL-2","ramo":"VIDA","servicios":[]}""")
        val servicios = (gateway.servicios("access-1", "POL-2") as ResultadoApi.Exito).valor
        assertTrue(servicios.vacia)
    }

    @Test
    fun cercanosEnviaTodosLosQueryYMapeaOrdenados() = runBlocking {
        responder(
            200,
            """{"poliza_id":"POL-1","servicio":"REPARACION_DISPOSITIVO",
                "ubicacion":{"latitud":4.711,"longitud":-74.072},
                "prestadores":[
                  {"prestador_id":"PREST-TEC-001","nombre":"Solventa Tech Centro",
                   "tipo_servicio":"REPARACION_DISPOSITIVO","direccion":"Dir 1","telefono":"3000000001",
                   "latitud":4.715,"longitud":-74.069,"distancia_km":0.55},
                  {"prestador_id":"PREST-TEC-002","nombre":"TechCare Norte",
                   "tipo_servicio":"REPARACION_DISPOSITIVO","direccion":"Dir 2","telefono":"3000000002",
                   "latitud":4.725,"longitud":-74.065,"distancia_km":1.75}]}"""
        )

        val resultado = gateway.prestadoresCercanos(
            "access-1", "POL-1", TipoServicio.REPARACION_DISPOSITIVO, 4.711, -74.072, 25.0
        )

        val cercanos = (resultado as ResultadoApi.Exito).valor
        assertEquals(listOf("PREST-TEC-001", "PREST-TEC-002"), cercanos.prestadores.map { it.prestadorId })
        assertEquals(0.55, cercanos.prestadores[0].distanciaKm, 0.0001)
        val peticion = servidor.takeRequest()
        assertTrue(peticion.path!!.startsWith("/api/v1/prestadores/cercanos"))
        assertTrue(peticion.path!!.contains("poliza_id=POL-1"))
        assertTrue(peticion.path!!.contains("servicio=REPARACION_DISPOSITIVO"))
        assertTrue(peticion.path!!.contains("radio_km=25.0"))
    }

    @Test
    fun solicitarHacePostSinClienteIdYDevuelveLaAsistencia() = runBlocking {
        responder(
            201,
            """{"asistencia_id":"ASI-1","poliza_id":"POL-1",
                "prestador":{"prestador_id":"PREST-TEC-001","nombre":"Solventa Tech Centro","telefono":"3000000001"},
                "servicio":"REPARACION_DISPOSITIVO","estado":"SOLICITADA",
                "ubicacion":{"latitud":4.711,"longitud":-74.072},
                "observaciones":"El dispositivo no enciende.","creada_en":"2026-11-15T14:30:00Z","cancelada_en":null}"""
        )

        val resultado = gateway.solicitar(
            "access-1",
            NuevaAsistencia(
                polizaId = "POL-1",
                prestadorId = "PREST-TEC-001",
                servicio = TipoServicio.REPARACION_DISPOSITIVO,
                latitud = 4.711,
                longitud = -74.072,
                observaciones = "El dispositivo no enciende."
            )
        )

        val asistencia = (resultado as ResultadoApi.Exito).valor
        assertEquals("ASI-1", asistencia.asistenciaId)
        assertEquals(EstadoAsistencia.SOLICITADA, asistencia.estado)
        val peticion = servidor.takeRequest()
        assertEquals("POST", peticion.method)
        assertEquals("/api/v1/asistencias", peticion.path)
        val cuerpo = peticion.body.readUtf8()
        assertTrue(cuerpo.contains("\"poliza_id\":\"POL-1\""))
        assertTrue(cuerpo.contains("\"servicio\":\"REPARACION_DISPOSITIVO\""))
        assertTrue(!cuerpo.contains("cliente_id"))
        assertTrue(!cuerpo.contains("\"estado\""))
    }

    @Test
    fun listarMapeaLasAsistencias() = runBlocking {
        responder(
            200,
            """[{"asistencia_id":"ASI-1","poliza_id":"POL-1",
                "prestador":{"prestador_id":"PREST-TEC-001","nombre":"Solventa Tech Centro","telefono":null},
                "servicio":"REPARACION_DISPOSITIVO","estado":"CANCELADA",
                "ubicacion":{"latitud":4.711,"longitud":-74.072},
                "observaciones":null,"creada_en":"2026-11-15T14:30:00Z","cancelada_en":"2026-11-15T15:00:00Z"}]"""
        )
        val lista = (gateway.listar("access-1") as ResultadoApi.Exito).valor
        assertEquals(1, lista.size)
        assertEquals(EstadoAsistencia.CANCELADA, lista[0].estado)
    }

    @Test
    fun listarMapeaAceptadaConEta() = runBlocking {
        responder(
            200,
            """[{"asistencia_id":"ASI-1","poliza_id":"POL-1",
                "prestador":{"prestador_id":"PREST-TEC-001","nombre":"Centro Técnico Madrid","telefono":"3000000000"},
                "servicio":"REPARACION_DISPOSITIVO","estado":"ACEPTADA",
                "ubicacion":{"latitud":4.711,"longitud":-74.072},
                "observaciones":null,"creada_en":"2026-11-15T14:30:00Z","cancelada_en":null,
                "aceptada_en":"2026-11-15T15:03:00Z","tiempo_estimado_llegada_minutos":20}]"""
        )
        val a = (gateway.listar("access-1") as ResultadoApi.Exito).valor.single()
        assertEquals(EstadoAsistencia.ACEPTADA, a.estado)
        assertEquals("2026-11-15T15:03:00Z", a.aceptadaEn)
        assertEquals(20, a.tiempoEstimadoLlegadaMinutos)
        assertTrue(a.aceptada)
    }

    @Test
    fun listarMapeaAceptadaSinEta() = runBlocking {
        responder(
            200,
            """[{"asistencia_id":"ASI-2","poliza_id":"POL-1",
                "prestador":{"prestador_id":"PREST-TEC-001","nombre":"Centro Técnico Madrid","telefono":null},
                "servicio":"REPARACION_DISPOSITIVO","estado":"ACEPTADA",
                "ubicacion":{"latitud":4.711,"longitud":-74.072},
                "observaciones":null,"creada_en":"2026-11-15T14:30:00Z","cancelada_en":null,
                "aceptada_en":"2026-11-15T15:03:00Z","tiempo_estimado_llegada_minutos":null}]"""
        )
        val a = (gateway.listar("access-1") as ResultadoApi.Exito).valor.single()
        assertEquals(EstadoAsistencia.ACEPTADA, a.estado)
        assertNull(a.tiempoEstimadoLlegadaMinutos)
    }

    @Test
    fun cancelarHacePostAlRecursoDeCancelacion() = runBlocking {
        responder(
            200,
            """{"asistencia_id":"ASI-1","poliza_id":"POL-1",
                "prestador":{"prestador_id":"PREST-TEC-001","nombre":"Solventa Tech Centro","telefono":null},
                "servicio":"REPARACION_DISPOSITIVO","estado":"CANCELADA",
                "ubicacion":{"latitud":4.711,"longitud":-74.072},
                "observaciones":null,"creada_en":"2026-11-15T14:30:00Z","cancelada_en":"2026-11-15T15:00:00Z"}"""
        )
        val resultado = gateway.cancelar("access-1", "ASI-1")
        assertEquals(EstadoAsistencia.CANCELADA, (resultado as ResultadoApi.Exito).valor.estado)
        val peticion = servidor.takeRequest()
        assertEquals("POST", peticion.method)
        assertEquals("/api/v1/asistencias/ASI-1/cancelacion", peticion.path)
    }

    @Test
    fun polizaAjenaDevuelve403ConCodigo() = runBlocking {
        responder(403, """{"detail":{"codigo":"POLIZA_NO_AUTORIZADA","mensaje":"No tiene acceso."}}""")
        assertEquals(
            ResultadoApi.Fallo(403, "POLIZA_NO_AUTORIZADA", "No tiene acceso."),
            gateway.servicios("access-1", "POL-X")
        )
    }

    @Test
    fun servicioIncompatibleDevuelve422ConCodigo() = runBlocking {
        responder(422, """{"detail":{"codigo":"SERVICIO_NO_DISPONIBLE","mensaje":"No ofrece."}}""")
        val resultado = gateway.prestadoresCercanos(
            "access-1", "POL-1", TipoServicio.ASISTENCIA_MEDICA, 4.711, -74.072, 25.0
        )
        assertEquals(ResultadoApi.Fallo(422, "SERVICIO_NO_DISPONIBLE", "No ofrece."), resultado)
    }

    @Test
    fun prestadorNoEncontradoDevuelve404() = runBlocking {
        responder(404, """{"detail":{"codigo":"PRESTADOR_NO_ENCONTRADO","mensaje":"No existe."}}""")
        val resultado = gateway.solicitar(
            "access-1",
            NuevaAsistencia("POL-1", "PREST-NO", TipoServicio.REPARACION_DISPOSITIVO, 4.711, -74.072, null)
        )
        assertEquals(ResultadoApi.Fallo(404, "PRESTADOR_NO_ENCONTRADO", "No existe."), resultado)
    }

    @Test
    fun errorDelServidor500EsFallo() = runBlocking {
        responder(500, "")
        assertTrue(gateway.listar("access-1") is ResultadoApi.Fallo)
    }

    @Test
    fun cuerpoQueNoEsJsonSeTrataComoFallo() = runBlocking {
        responder(200, "<html>proxy</html>")
        assertTrue(gateway.servicios("access-1", "POL-1") is ResultadoApi.Fallo)
    }

    @Test
    fun sinServidorDevuelveSinConexion() = runBlocking {
        servidor.shutdown()
        assertEquals(ResultadoApi.SinConexion, gateway.listar("access-1"))
    }
}
