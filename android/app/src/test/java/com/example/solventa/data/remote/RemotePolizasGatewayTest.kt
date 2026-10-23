package com.example.solventa.data.remote

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.EnlaceCompartido
import com.example.solventa.domain.polizas.EstadoPoliza
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/** HU07: el gateway de la billetera contra un servidor HTTP falso, con Retrofit y Gson reales. */
class RemotePolizasGatewayTest {
    private lateinit var servidor: MockWebServer
    private lateinit var gateway: RemotePolizasGateway

    @Before
    fun iniciar() {
        servidor = MockWebServer()
        servidor.start()
        gateway = RemotePolizasGateway(ApiClient.crearPolizasApi(servidor.url("/").toString()))
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

    private val billeteraJson = """
        {"polizas":[
          {"poliza_id":"POL-1","numero_poliza":"SOL-VJ-0001","ramo":"VIAJE",
           "nombre_ramo":"Seguro de viaje","estado":"VIGENTE","activa":true,
           "fecha_inicio":"2026-10-01","fecha_fin":"2026-12-31",
           "cobertura_principal":"Asistencia médica en viaje"},
          {"poliza_id":"POL-2","numero_poliza":"SOL-VD-0002","ramo":"VIDA",
           "nombre_ramo":"Seguro de vida","estado":"VENCIDA","activa":false,
           "fecha_inicio":"2025-01-01","fecha_fin":"2025-12-31",
           "cobertura_principal":"Muerte por cualquier causa"}
        ],"total_vigentes":1,"total_inactivas":1}
    """.trimIndent()

    @Test
    fun billeteraEnviaElTokenYMapeaLasPolizas() = runBlocking {
        responder(200, billeteraJson)

        val resultado = gateway.billetera("access-1")

        val billetera = (resultado as ResultadoApi.Exito).valor
        assertEquals(listOf("POL-1", "POL-2"), billetera.polizas.map { it.polizaId })
        assertEquals(EstadoPoliza.VENCIDA, billetera.polizas[1].estado)
        assertEquals(1, billetera.totalVigentes)
        assertEquals(1, billetera.totalInactivas)

        val peticion = servidor.takeRequest()
        assertEquals("GET", peticion.method)
        assertEquals("/api/v1/billetera/polizas", peticion.path)
        assertEquals("Bearer access-1", peticion.getHeader("Authorization"))
    }

    @Test
    fun descartaPolizasIncompletasOConEstadoDesconocido() = runBlocking {
        responder(
            200,
            """{"polizas":[{"poliza_id":"X","estado":"RARO"},{"numero_poliza":"Y"}],
                "total_vigentes":5,"total_inactivas":0}"""
        )

        val billetera = (gateway.billetera("access-1") as ResultadoApi.Exito).valor

        assertTrue(billetera.vacia)
        assertEquals(0, billetera.totalVigentes)
    }

    @Test
    fun certificadoUsaLaRutaDeLaPoliza() = runBlocking {
        responder(
            200,
            """{"poliza_id":"POL-1","numero_poliza":"SOL-VJ-0001","ramo":"VIAJE",
                "nombre_ramo":"Seguro de viaje","estado":"VIGENTE","activa":true,
                "titular":"Ana Pérez","documento_titular":"CC ****5678",
                "fecha_inicio":"2026-10-01","fecha_fin":"2026-12-31",
                "cobertura_principal":"Asistencia médica en viaje",
                "suma_asegurada":"40000000.00","prima_total":"85000.00","moneda":"COP",
                "emitida_en":"2026-09-30T14:00:00Z","contenido_qr":"SOLVENTA|SOL-VJ-0001|abc"}"""
        )

        val certificado = (gateway.certificado("access-1", "POL-1") as ResultadoApi.Exito).valor

        assertEquals("SOLVENTA|SOL-VJ-0001|abc", certificado.contenidoQr)
        assertEquals("CC ****5678", certificado.documentoTitular)
        assertEquals("40000000.00", certificado.sumaAsegurada)
        assertEquals("/api/v1/billetera/polizas/POL-1/certificado", servidor.takeRequest().path)
    }

    @Test
    fun certificadoDeOtroTitularDevuelve404ConElCodigo() = runBlocking {
        responder(404, """{"detail":{"codigo":"POLIZA_NO_ENCONTRADA","mensaje":"No encontramos esa póliza."}}""")

        val resultado = gateway.certificado("access-1", "POL-9")

        assertEquals(ResultadoApi.Fallo(404, "POLIZA_NO_ENCONTRADA", "No encontramos esa póliza."), resultado)
    }

    @Test
    fun compartirHaceUnPostYDevuelveElEnlace() = runBlocking {
        responder(
            201,
            """{"url":"https://api.solventa.co/api/v1/certificados-compartidos/abc",
                "expira_en":"2026-10-22T15:00:00Z"}"""
        )

        val resultado = gateway.compartir("access-1", "POL-1")

        assertEquals(
            ResultadoApi.Exito(
                EnlaceCompartido(
                    "https://api.solventa.co/api/v1/certificados-compartidos/abc",
                    "2026-10-22T15:00:00Z"
                )
            ),
            resultado
        )
        val peticion = servidor.takeRequest()
        assertEquals("POST", peticion.method)
        assertEquals("/api/v1/billetera/polizas/POL-1/enlaces", peticion.path)
    }

    @Test
    fun unEnlaceQueNoEsHttpSeRechaza() = runBlocking {
        responder(201, """{"url":"javascript:alert(1)","expira_en":"2026-10-22T15:00:00Z"}""")

        assertEquals(ResultadoApi.Fallo(201, null, null), gateway.compartir("access-1", "POL-1"))
    }

    @Test
    fun tokenRechazadoDevuelve401() = runBlocking {
        responder(401, """{"detail":{"codigo":"TOKEN_EXPIRED","mensaje":"El token expiró."}}""")

        assertEquals(
            ResultadoApi.Fallo(401, "TOKEN_EXPIRED", "El token expiró."),
            gateway.billetera("access-viejo")
        )
    }

    @Test
    fun cuerpoQueNoEsJsonSeTrataComoFallo() = runBlocking {
        responder(200, "<html>proxy</html>")

        assertTrue(gateway.billetera("access-1") is ResultadoApi.Fallo)
    }

    @Test
    fun sinServidorDevuelveSinConexion() = runBlocking {
        servidor.shutdown()

        assertEquals(ResultadoApi.SinConexion, gateway.billetera("access-1"))
    }
}
