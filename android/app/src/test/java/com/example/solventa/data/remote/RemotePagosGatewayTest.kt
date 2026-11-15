package com.example.solventa.data.remote

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.pagos.ConceptoPago
import com.example.solventa.domain.pagos.EstadoPago
import com.example.solventa.domain.pagos.MetodoPago
import com.example.solventa.domain.pagos.SolicitudPago
import com.example.solventa.domain.pagos.TipoPrimaPendiente
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

    @Test
    fun elPagoTraeSuConceptoYSinElEsUnaCompra() = runBlocking {
        servidor.enqueue(
            MockResponse().setResponseCode(200).setHeader("Content-Type", "application/json")
                .setBody(PAGO_APROBADO_JSON.replace("\"estado\"", "\"concepto\":\"RENOVACION\",\"estado\""))
        )
        servidor.enqueue(
            MockResponse().setResponseCode(200).setHeader("Content-Type", "application/json")
                .setBody(PAGO_APROBADO_JSON)
        )

        val renovacion = gateway.consultar("access-1", "PAG-1") as ResultadoApi.Exito
        val compra = gateway.consultar("access-1", "PAG-1") as ResultadoApi.Exito

        assertEquals(ConceptoPago.RENOVACION, renovacion.valor.concepto)
        assertEquals(ConceptoPago.COMPRA, compra.valor.concepto)
    }

    @Test
    fun listaLasPrimasPendientesYDescartaLasIncompletas() = runBlocking {
        servidor.enqueue(
            MockResponse().setResponseCode(200).setHeader("Content-Type", "application/json")
                .setBody(
                    """
                    {"total":3,"primas":[
                      {"tipo":"RENOVACION","accion":"PAGAR","referencia_id":"REN-1","cotizacion_id":"COT-R",
                       "poliza_id":"POL-1","numero_poliza":"SOL-2026-0001","ramo":"VIDA",
                       "nombre_ramo":"Microseguro de vida","monto":"420000.00","moneda":"COP",
                       "fecha_limite":"2026-12-31T23:59:59-05:00","mensaje":null},
                      {"tipo":"FIRMA_PENDIENTE","accion":"FIRMAR","referencia_id":"COT-F","cotizacion_id":"COT-F",
                       "poliza_id":null,"numero_poliza":null,"ramo":"VIDA","nombre_ramo":"Microseguro de vida",
                       "monto":"89000.00","moneda":"COP","fecha_limite":null,
                       "mensaje":"Firma tu contrato en el portal web para emitir tu póliza."},
                      {"tipo":"DESCONOCIDO","referencia_id":"X","cotizacion_id":"X","monto":"1.00","moneda":"COP"}
                    ]}
                    """.trimIndent()
                )
        )

        val respuesta = gateway.pendientes("access-1") as ResultadoApi.Exito

        val primas = respuesta.valor
        assertEquals(2, primas.size)
        assertEquals(TipoPrimaPendiente.RENOVACION, primas[0].tipo)
        assertEquals("SOL-2026-0001", primas[0].numeroPoliza)
        assertEquals("420000.00", primas[0].monto.toPlainString())
        assertEquals(true, primas[0].sePaga)
        assertEquals(TipoPrimaPendiente.FIRMA_PENDIENTE, primas[1].tipo)
        assertEquals(false, primas[1].sePaga)
        val peticion = servidor.takeRequest()
        assertEquals("GET", peticion.method)
        assertEquals("/api/v1/primas-pendientes", peticion.path)
        assertEquals("Bearer access-1", peticion.getHeader("Authorization"))
    }

    @Test
    fun consultaElComprobanteDeUnPago() = runBlocking {
        servidor.enqueue(
            MockResponse().setResponseCode(200).setHeader("Content-Type", "application/json")
                .setBody(
                    """
                    {"numero":"CP-20261210-ABCD1234","pago_id":"PAG-1","concepto":"RENOVACION",
                     "descripcion":"Renovación de la póliza SOL-2026-0001 (Microseguro de vida)",
                     "poliza_id":"POL-1","numero_poliza":"SOL-2026-0001","monto":"420000.00",
                     "moneda":"COP","metodo":"TARJETA","referencia_pasarela":"PSP-1",
                     "pagado_en":"2026-12-10T15:00:00Z"}
                    """.trimIndent()
                )
        )

        val comprobante = (gateway.comprobante("access-1", "PAG-1") as ResultadoApi.Exito).valor

        assertEquals("CP-20261210-ABCD1234", comprobante.numero)
        assertEquals(ConceptoPago.RENOVACION, comprobante.concepto)
        assertEquals("POL-1", comprobante.polizaId)
        assertEquals("420000.00", comprobante.monto.toPlainString())
        assertEquals("/api/v1/pagos/PAG-1/comprobante", servidor.takeRequest().path)
    }

    @Test
    fun elComprobanteDeUnPagoSinAprobarEsUnFallo() = runBlocking {
        servidor.enqueue(
            MockResponse().setResponseCode(409).setHeader("Content-Type", "application/json")
                .setBody("""{"detail":{"codigo":"PAGO_SIN_COMPROBANTE","mensaje":"Aún no está aprobado."}}""")
        )

        val respuesta = gateway.comprobante("access-1", "PAG-1")

        val fallo = respuesta as ResultadoApi.Fallo
        assertEquals(409, fallo.http)
        assertEquals("PAGO_SIN_COMPROBANTE", fallo.codigo)
    }

    @Test
    fun unComprobanteIncompletoSeTrataComoFallo() = runBlocking {
        servidor.enqueue(
            MockResponse().setResponseCode(200).setHeader("Content-Type", "application/json")
                .setBody("""{"numero":"CP-1"}""")
        )

        assertEquals(true, gateway.comprobante("access-1", "PAG-1") is ResultadoApi.Fallo)
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
