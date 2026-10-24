package com.example.solventa.data.remote

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.pagos.EstadoPago
import com.example.solventa.domain.pagos.MetodoPago
import com.example.solventa.domain.pagos.SolicitudPago
import com.google.gson.JsonParser
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

/** HU13: integración HTTP del recaudo Android contra el contrato real. */
class RemotePagosGatewayTest {
    private lateinit var servidor: MockWebServer
    private lateinit var gateway: RemotePagosGateway

    @Before
    fun iniciar() {
        servidor = MockWebServer()
        servidor.start()
        gateway = RemotePagosGateway(ApiClient.crearPagosApi(servidor.url("/").toString()))
    }

    @After
    fun detener() {
        servidor.shutdown()
    }

    @Test
    fun enviaLaIdempotencyKeyYElCuerpoYUsaElPagoDelBackend() = runBlocking {
        servidor.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setHeader("Content-Type", "application/json")
                .setBody(PAGO_APROBADO_JSON)
        )

        val respuesta = gateway.pagar(
            accessToken = "access-1",
            idempotencyKey = "llave-abc",
            solicitud = SolicitudPago(
                cotizacionId = "COT-1",
                metodo = MetodoPago.TARJETA,
                tokenTarjeta = "tok_visa_123456"
            )
        )

        val pago = (respuesta as ResultadoApi.Exito).valor
        assertEquals(EstadoPago.APROBADO, pago.estado)
        assertEquals("45000.00", pago.monto.toPlainString())

        val peticion = servidor.takeRequest()
        assertEquals("POST", peticion.method)
        assertEquals("/api/v1/pagos", peticion.path)
        assertEquals("Bearer access-1", peticion.getHeader("Authorization"))
        assertEquals("llave-abc", peticion.getHeader("Idempotency-Key"))
        val json = JsonParser.parseString(peticion.body.readUtf8()).asJsonObject
        assertEquals("COT-1", json["cotizacion_id"].asString)
        assertEquals("TARJETA", json["metodo"].asString)
        assertEquals("tok_visa_123456", json["token_tarjeta"].asString)
    }

    @Test
    fun pseDevuelveUrlDeRedireccionYEstadoPendiente() = runBlocking {
        servidor.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setHeader("Content-Type", "application/json")
                .setBody(PAGO_PSE_JSON)
        )

        val respuesta = gateway.pagar(
            accessToken = "access-1",
            idempotencyKey = "llave-pse",
            solicitud = SolicitudPago(
                cotizacionId = "COT-1",
                metodo = MetodoPago.PSE,
                codigoBanco = "1007"
            )
        )

        val pago = (respuesta as ResultadoApi.Exito).valor
        assertEquals(EstadoPago.PENDIENTE, pago.estado)
        assertEquals("https://portal/pse/PSP-1", pago.urlRedireccion)
    }

    @Test
    fun conservaElErrorEstructuradoDelBackend() = runBlocking {
        servidor.enqueue(
            MockResponse()
                .setResponseCode(409)
                .setHeader("Content-Type", "application/json")
                .setBody(
                    """{"detail":{"codigo":"COTIZACION_NO_VIGENTE","mensaje":"La cotización no está vigente."}}"""
                )
        )

        val respuesta = gateway.pagar(
            "access-1",
            "llave-x",
            SolicitudPago("COT-1", MetodoPago.TARJETA, tokenTarjeta = "tok_visa_1")
        )

        assertEquals(
            ResultadoApi.Fallo(409, "COTIZACION_NO_VIGENTE", "La cotización no está vigente."),
            respuesta
        )
    }

    @Test
    fun consultaUnPagoPorSuIdentificador() = runBlocking {
        servidor.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody(PAGO_APROBADO_JSON)
        )

        val respuesta = gateway.consultar("access-1", "PAG-1")

        assertEquals(EstadoPago.APROBADO, (respuesta as ResultadoApi.Exito).valor.estado)
        val peticion = servidor.takeRequest()
        assertEquals("GET", peticion.method)
        assertEquals("/api/v1/pagos/PAG-1", peticion.path)
        assertEquals("Bearer access-1", peticion.getHeader("Authorization"))
    }

    private companion object {
        val PAGO_APROBADO_JSON = """
            {
              "pago_id":"PAG-1",
              "cotizacion_id":"COT-1",
              "metodo":"TARJETA",
              "monto":"45000.00",
              "moneda":"COP",
              "estado":"APROBADO",
              "motivo_rechazo":null,
              "url_redireccion":null,
              "referencia_pasarela":"PSP-1"
            }
        """.trimIndent()

        val PAGO_PSE_JSON = """
            {
              "pago_id":"PAG-2",
              "cotizacion_id":"COT-1",
              "metodo":"PSE",
              "monto":"45000.00",
              "moneda":"COP",
              "estado":"PENDIENTE",
              "motivo_rechazo":null,
              "url_redireccion":"https://portal/pse/PSP-1",
              "referencia_pasarela":"PSP-1"
            }
        """.trimIndent()
    }
}
