package com.example.solventa.data.remote

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.notificaciones.TipoNotificacion
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/** HU05: el gateway de notificaciones contra un servidor HTTP falso, con Retrofit y Gson reales. */
class RemoteNotificacionesGatewayTest {
    private lateinit var servidor: MockWebServer
    private lateinit var gateway: RemoteNotificacionesGateway

    @Before
    fun iniciar() {
        servidor = MockWebServer()
        servidor.start()
        gateway = RemoteNotificacionesGateway(
            ApiClient.crearNotificacionesApi(servidor.url("/").toString())
        )
    }

    @After
    fun detener() {
        try {
            servidor.shutdown()
        } catch (ignorado: Exception) {
            // Alguna prueba ya lo apagó.
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

    @Test
    fun listaLaBandejaYDescartaLoQueNoSeEntiende() = runBlocking {
        responder(
            200,
            """
            {"notificaciones":[
              {"notificacion_id":"N-1","tipo":"PAGO_PARAMETRICO","titulo":"Pago aprobado",
               "cuerpo":"Se aprobó un pago.","datos":{"siniestro_id":"SIN-1"},
               "creada_en":"2026-12-10T15:00:00Z","leida":false},
              {"notificacion_id":"N-2","tipo":"TIPO_NUEVO","titulo":"Algo","cuerpo":"x",
               "datos":{},"creada_en":"2026-12-10T15:00:00Z","leida":false},
              {"notificacion_id":null,"tipo":"ESTADO_SINIESTRO","titulo":"Sin id"}
            ],"no_leidas":3}
            """.trimIndent()
        )

        val resultado = gateway.listar("access-1")

        val bandeja = (resultado as ResultadoApi.Exito).valor
        assertEquals(listOf("N-1"), bandeja.notificaciones.map { it.notificacionId })
        assertEquals(TipoNotificacion.PAGO_PARAMETRICO, bandeja.notificaciones.first().tipo)
        assertEquals("SIN-1", bandeja.notificaciones.first().datos["siniestro_id"])
        assertEquals(3, bandeja.noLeidas)
        val peticion = servidor.takeRequest()
        assertEquals("Bearer access-1", peticion.getHeader("Authorization"))
        assertTrue(peticion.path!!.startsWith("/api/v1/notificaciones"))
    }

    @Test
    fun sinConteoLaInsigniaSaleDeLasNoLeidasDeLaLista() = runBlocking {
        responder(
            200,
            """{"notificaciones":[
              {"notificacion_id":"N-1","tipo":"ESTADO_SINIESTRO","titulo":"t","cuerpo":"c",
               "datos":{"siniestro_id":"S"},"creada_en":"2026-12-10T15:00:00Z","leida":false}]}"""
        )

        val bandeja = (gateway.listar("a") as ResultadoApi.Exito).valor

        assertEquals(1, bandeja.noLeidas)
    }

    @Test
    fun cuentaLasNoLeidas() = runBlocking {
        responder(200, """{"no_leidas":5}""")

        assertEquals(5, (gateway.contarNoLeidas("a") as ResultadoApi.Exito).valor)
        assertEquals("/api/v1/notificaciones/no-leidas", servidor.takeRequest().path)
    }

    @Test
    fun marcaUnaComoLeida() = runBlocking {
        responder(200, """{"notificacion_id":"N-1","leida":true,"no_leidas":2}""")

        assertEquals(2, (gateway.marcarLeida("a", "N-1") as ResultadoApi.Exito).valor)
        val peticion = servidor.takeRequest()
        assertEquals("POST", peticion.method)
        assertEquals("/api/v1/notificaciones/N-1/leida", peticion.path)
    }

    @Test
    fun registraElDispositivoConUn204() = runBlocking {
        responder(204)

        assertTrue(gateway.registrarDispositivo("a", "tok-1") is ResultadoApi.Exito)
        val peticion = servidor.takeRequest()
        assertEquals("PUT", peticion.method)
        assertEquals("/api/v1/notificaciones/dispositivos", peticion.path)
        val cuerpo = peticion.body.readUtf8()
        assertTrue(cuerpo, cuerpo.contains("\"token\":\"tok-1\""))
        assertTrue(cuerpo, cuerpo.contains("\"plataforma\":\"ANDROID\""))
    }

    @Test
    fun daDeBajaElDispositivo() = runBlocking {
        responder(204)

        assertTrue(gateway.darDeBajaDispositivo("a", "tok-1") is ResultadoApi.Exito)
        val peticion = servidor.takeRequest()
        assertEquals("POST", peticion.method)
        assertEquals("/api/v1/notificaciones/dispositivos/baja", peticion.path)
    }

    @Test
    fun leeYCambiaLaPreferencia() = runBlocking {
        responder(200, """{"push_habilitado":false}""")
        responder(200, """{"push_habilitado":true}""")

        assertEquals(false, (gateway.obtenerPreferencia("a") as ResultadoApi.Exito).valor)
        assertEquals(true, (gateway.cambiarPreferencia("a", true) as ResultadoApi.Exito).valor)
        servidor.takeRequest()
        val cambio = servidor.takeRequest()
        assertEquals("PUT", cambio.method)
        assertEquals("""{"push_habilitado":true}""", cambio.body.readUtf8())
    }

    @Test
    fun unaRespuestaDeErrorSeConvierteEnFallo() = runBlocking {
        responder(401, """{"detail":{"codigo":"TOKEN_EXPIRED","mensaje":"El token expiró."}}""")

        val resultado = gateway.listar("a")

        assertEquals(401, (resultado as ResultadoApi.Fallo).http)
    }

    @Test
    fun unCuerpoExitosoSinElCampoEsperadoEsUnFallo() = runBlocking {
        responder(200, """{"no_leidas":null}""")

        assertTrue(gateway.contarNoLeidas("a") is ResultadoApi.Fallo)
    }

    @Test
    fun unJsonRotoEsUnFalloYNoUnaExcepcion() = runBlocking {
        responder(200, "{no es json")

        assertTrue(gateway.listar("a") is ResultadoApi.Fallo)
    }

    @Test
    fun sinServidorEsSinConexion() = runBlocking {
        servidor.shutdown()

        assertEquals(ResultadoApi.SinConexion, gateway.listar("a"))
        assertEquals(ResultadoApi.SinConexion, gateway.registrarDispositivo("a", "t"))
    }
}
