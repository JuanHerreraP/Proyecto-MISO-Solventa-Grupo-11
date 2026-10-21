package com.example.solventa.data.remote

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.google.gson.JsonParser
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/** BPM-25: integración HTTP de la cotización Android contra el contrato real. */
class RemoteCotizacionesGatewayTest {
    private lateinit var servidor: MockWebServer
    private lateinit var gateway: RemoteCotizacionesGateway

    @Before
    fun iniciar() {
        servidor = MockWebServer()
        servidor.start()
        gateway = RemoteCotizacionesGateway(ApiClient.crearCotizacionesApi(servidor.url("/").toString()))
    }

    @After
    fun detener() {
        servidor.shutdown()
    }

    @Test
    fun enviaDatosTipadosYUsaElResultadoCalculadoPorElBackend() = runBlocking {
        servidor.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setHeader("Content-Type", "application/json")
                .setBody(COTIZACION_JSON)
        )

        val respuesta = gateway.cotizar(
            accessToken = "access-1",
            clienteId = "CLI-1",
            ramo = RamoCotizacion.VIAJE,
            datosRiesgo = mapOf(
                "destino" to "Japón",
                "fecha_inicio" to "2026-11-01",
                "fecha_fin" to "2026-11-08",
                "numero_viajeros" to 1,
                "valor_asegurado" to 20_000_000.toBigDecimal()
            )
        )

        val cotizacion = (respuesta as ResultadoApi.Exito).valor
        assertEquals("21000.00", cotizacion.primaTotal.toPlainString())
        assertEquals("20000000.00", cotizacion.coberturaPrincipal.sumaAsegurada.toPlainString())

        val peticion = servidor.takeRequest()
        assertEquals("POST", peticion.method)
        assertEquals("/api/v1/cotizaciones", peticion.path)
        assertEquals("Bearer access-1", peticion.getHeader("Authorization"))
        val json = JsonParser.parseString(peticion.body.readUtf8()).asJsonObject
        assertEquals("CLI-1", json["cliente_id"].asString)
        assertEquals("VIAJE", json["ramo"].asString)
        assertTrue(json["datos_riesgo"].asJsonObject["numero_viajeros"].isJsonPrimitive)
        assertEquals(20_000_000, json["datos_riesgo"].asJsonObject["valor_asegurado"].asInt)
    }

    @Test
    fun conservaElErrorEstructuradoDelBackend() = runBlocking {
        servidor.enqueue(
            MockResponse()
                .setResponseCode(422)
                .setHeader("Content-Type", "application/json")
                .setBody(
                    """{"detail":{"codigo":"DATOS_RIESGO_INVALIDOS","mensaje":"Fechas inválidas."}}"""
                )
        )

        val respuesta = gateway.cotizar("access-1", "CLI-1", RamoCotizacion.VIAJE, emptyMap())

        assertEquals(
            ResultadoApi.Fallo(422, "DATOS_RIESGO_INVALIDOS", "Fechas inválidas."),
            respuesta
        )
    }

    private companion object {
        val COTIZACION_JSON = """
            {
              "cotizacion_id":"COT-1",
              "cliente_id":"CLI-1",
              "ramo":"VIAJE",
              "datos_riesgo":{},
              "estado":"VIGENTE",
              "prima_total":"21000.00",
              "moneda":"COP",
              "cobertura_principal":{
                "codigo":"ASISTENCIA_VIAJE",
                "nombre":"Asistencia integral de viaje",
                "suma_asegurada":"20000000.00",
                "descripcion":"Atención de emergencias cubiertas durante el viaje contratado."
              },
              "perfil_riesgo_id":null,
              "asesor_id":null,
              "socio_id":null,
              "tenant_id":null,
              "creada_en":"2026-10-21T12:00:00Z",
              "vigente_hasta":"2026-10-22T12:00:00Z"
            }
        """.trimIndent()
    }
}
