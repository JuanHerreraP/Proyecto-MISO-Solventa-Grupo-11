package com.example.solventa.data.remote

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.siniestros.EstadoSiniestro
import com.example.solventa.domain.siniestros.OrigenSiniestro
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/** HU20: el gateway de siniestros contra un servidor HTTP falso, con Retrofit y Gson reales. */
class RemoteSiniestrosGatewayTest {
    private lateinit var servidor: MockWebServer
    private lateinit var gateway: RemoteSiniestrosGateway

    @Before
    fun iniciar() {
        servidor = MockWebServer()
        servidor.start()
        gateway = RemoteSiniestrosGateway(ApiClient.crearSiniestrosApi(servidor.url("/").toString()))
    }

    @After
    fun detener() {
        try {
            servidor.shutdown()
        } catch (ignorado: Exception) {
            // Algunas pruebas ya lo apagaron.
        }
    }

    private fun responder(codigo: Int, cuerpo: String = "") {
        servidor.enqueue(
            MockResponse()
                .setResponseCode(codigo)
                .setHeader("Content-Type", "application/json")
                .setBody(cuerpo)
        )
    }

    private val listaJson = """
        [
          {"siniestro_id":"SIN-1","cliente_id":"CLI-1","poliza_id":"DEMO-04",
           "origen":"AUTOMATICO","estado":"REGISTRADO","evento_id":"FLIGHT-AV123-20261026-abc",
           "fecha_evento":"2026-10-26","hora_evento":"20:00:00","lugar":"BOG",
           "descripcion":"Siniestro paramétrico automático.","estimacion_danos":"500000.00",
           "moneda":"COP","registrado_por":"TELEMETRIA","registrado_en":"2026-10-26T20:01:00Z"},
          {"siniestro_id":"SIN-2","cliente_id":"CLI-1","poliza_id":"POL-9",
           "origen":"MANUAL","estado":"EN_EVALUACION","evento_id":null,
           "fecha_evento":"2026-10-20","hora_evento":"18:30:00","lugar":"Aeropuerto",
           "descripcion":"Vuelo cancelado.","estimacion_danos":"850000.00",
           "moneda":"COP","registrado_por":"CLI-1","registrado_en":"2026-10-20T19:00:00Z"}
        ]
    """.trimIndent()

    @Test
    fun listarEnviaElTokenYMapeaLosSiniestros() = runBlocking {
        responder(200, listaJson)

        val resultado = gateway.listar("access-1")

        val siniestros = (resultado as ResultadoApi.Exito).valor
        assertEquals(listOf("SIN-1", "SIN-2"), siniestros.siniestros.map { it.siniestroId })
        assertEquals(OrigenSiniestro.AUTOMATICO, siniestros.siniestros[0].origen)
        assertEquals("FLIGHT-AV123-20261026-abc", siniestros.siniestros[0].eventoId)
        assertEquals(EstadoSiniestro.EN_EVALUACION, siniestros.siniestros[1].estado)
        assertNull(siniestros.siniestros[1].eventoId)
        assertEquals(1, siniestros.automaticos)

        val peticion = servidor.takeRequest()
        assertEquals("GET", peticion.method)
        assertEquals("/api/v1/siniestros", peticion.path)
        assertEquals("Bearer access-1", peticion.getHeader("Authorization"))
    }

    @Test
    fun listaVaciaEsExitoSinSiniestros() = runBlocking {
        responder(200, "[]")

        val siniestros = (gateway.listar("access-1") as ResultadoApi.Exito).valor

        assertTrue(siniestros.vacia)
        assertEquals(0, siniestros.total)
    }

    @Test
    fun descartaSiniestrosIncompletosOConEstadoDesconocido() = runBlocking {
        responder(
            200,
            """[{"siniestro_id":"X","origen":"AUTOMATICO","estado":"RARO"},
                {"poliza_id":"Y"}]"""
        )

        val siniestros = (gateway.listar("access-1") as ResultadoApi.Exito).valor

        assertTrue(siniestros.vacia)
    }

    @Test
    fun tokenRechazadoDevuelve401ConElCodigo() = runBlocking {
        responder(401, """{"detail":{"codigo":"TOKEN_EXPIRED","mensaje":"El token expiró."}}""")

        assertEquals(
            ResultadoApi.Fallo(401, "TOKEN_EXPIRED", "El token expiró."),
            gateway.listar("access-viejo")
        )
    }

    @Test
    fun cuerpoQueNoEsJsonSeTrataComoFallo() = runBlocking {
        responder(200, "<html>proxy</html>")

        assertTrue(gateway.listar("access-1") is ResultadoApi.Fallo)
    }

    @Test
    fun sinServidorDevuelveSinConexion() = runBlocking {
        servidor.shutdown()

        assertEquals(ResultadoApi.SinConexion, gateway.listar("access-1"))
    }

    @Test
    fun registrarHaceUnPostConElCuerpoYDevuelveElSiniestro() = runBlocking {
        responder(
            201,
            """{"siniestro_id":"SIN-NUEVO","cliente_id":"CLI-1","poliza_id":"POL-1",
                "origen":"MANUAL","estado":"REGISTRADO","evento_id":null,
                "fecha_evento":"2026-10-20","hora_evento":"18:30:00","lugar":"El Dorado",
                "descripcion":"Vuelo cancelado y gastos.","estimacion_danos":"850000.00",
                "moneda":"COP","registrado_por":"CLI-1","registrado_en":"2026-10-21T10:00:00Z"}"""
        )

        val resultado = gateway.registrar(
            "access-1",
            com.example.solventa.domain.siniestros.SolicitudSiniestro(
                polizaId = "POL-1",
                fechaEvento = "2026-10-20",
                horaEvento = "18:30:00",
                lugar = "El Dorado",
                descripcion = "Vuelo cancelado y gastos.",
                estimacionDanos = "850000"
            )
        )

        val siniestro = (resultado as ResultadoApi.Exito).valor
        assertEquals("SIN-NUEVO", siniestro.siniestroId)
        assertEquals(OrigenSiniestro.MANUAL, siniestro.origen)

        val peticion = servidor.takeRequest()
        assertEquals("POST", peticion.method)
        assertEquals("/api/v1/siniestros", peticion.path)
        assertEquals("Bearer access-1", peticion.getHeader("Authorization"))
        val cuerpo = peticion.body.readUtf8()
        assertTrue(cuerpo.contains("\"poliza_id\":\"POL-1\""))
        assertTrue(cuerpo.contains("\"hora_evento\":\"18:30:00\""))
        // El cliente nunca envía su identificador.
        assertTrue(!cuerpo.contains("cliente_id"))
    }

    @Test
    fun registrarPolizaNoVigenteDevuelve409ConElCodigo() = runBlocking {
        responder(409, """{"detail":{"codigo":"POLIZA_NO_VIGENTE","mensaje":"La póliza no está vigente."}}""")

        val resultado = gateway.registrar(
            "access-1",
            com.example.solventa.domain.siniestros.SolicitudSiniestro(
                "POL-1", "2024-01-01", "10:00:00", "X", "Descripción larga.", "1000"
            )
        )

        assertEquals(
            ResultadoApi.Fallo(409, "POLIZA_NO_VIGENTE", "La póliza no está vigente."),
            resultado
        )
    }
}
