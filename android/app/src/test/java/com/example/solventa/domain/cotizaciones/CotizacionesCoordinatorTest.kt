package com.example.solventa.domain.cotizaciones

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.SesionAutenticada
import java.math.BigDecimal
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CotizacionesCoordinatorTest {
    private val gateway = GatewayFalso()
    private val sesion = SesionFalsa()
    private val coordinador = CotizacionesCoordinator(gateway, sesion)

    @Test
    fun convierteLosCamposYConservaLaPrimaYCoberturaDelBackend() = runBlocking {
        coordinador.cotizar(
            clienteId = "CLI-1",
            ramo = RamoCotizacion.VIAJE,
            valores = mapOf(
                "destino" to "Japón",
                "fecha_inicio" to "2026-11-01",
                "fecha_fin" to "2026-11-08",
                "numero_viajeros" to "1",
                "valor_asegurado" to "20000000"
            )
        )

        assertEquals("access-1", gateway.token)
        assertEquals("CLI-1", gateway.clienteId)
        assertEquals(1, gateway.datos["numero_viajeros"])
        assertEquals(BigDecimal("20000000"), gateway.datos["valor_asegurado"])
        assertEquals(BigDecimal("21000.00"), coordinador.estado.resultado?.primaTotal)
        assertEquals(
            BigDecimal("20000000.00"),
            coordinador.estado.resultado?.coberturaPrincipal?.sumaAsegurada
        )
        assertFalse(coordinador.estado.cargando)
        assertNull(coordinador.estado.error)
    }

    @Test
    fun datoNumericoInvalidoNoLlamaLaApi() = runBlocking {
        coordinador.cotizar(
            "CLI-1",
            RamoCotizacion.VIAJE,
            mapOf("numero_viajeros" to "uno")
        )

        assertFalse(gateway.llamado)
        assertEquals(MensajesCotizaciones.DATOS_INVALIDOS, coordinador.estado.error)
    }

    @Test
    fun tokenRechazadoCierraLaSesion() = runBlocking {
        gateway.respuesta = ResultadoApi.Fallo(401, "TOKEN_EXPIRED", "El token expiró.")

        coordinador.cotizar("CLI-1", RamoCotizacion.VIAJE, emptyMap())

        assertEquals(1, sesion.rechazos)
        assertEquals(MensajesCotizaciones.SESION_VENCIDA, coordinador.estado.error)
    }

    @Test
    fun limpiarDescartaElResultado() = runBlocking {
        coordinador.cotizar("CLI-1", RamoCotizacion.VIAJE, emptyMap())
        assertTrue(coordinador.estado.resultado != null)

        coordinador.limpiar()

        assertEquals(EstadoCotizaciones(), coordinador.estado)
    }

    @Test
    fun listaLasCotizacionesDelClienteAutenticado() = runBlocking {
        coordinador.listar("CLI-1")

        assertEquals("CLI-1", gateway.clienteListado)
        assertEquals(listOf(resultado()), coordinador.estado.listado)
        assertFalse(coordinador.estado.cargandoListado)
        assertNull(coordinador.estado.errorListado)
    }

    @Test
    fun conservaElListadoYExponeErrorSiFallaLaActualizacion() = runBlocking {
        coordinador.listar("CLI-1")
        gateway.respuestaListado = ResultadoApi.SinConexion

        coordinador.listar("CLI-1")

        assertEquals(listOf(resultado()), coordinador.estado.listado)
        assertEquals(MensajesCotizaciones.SIN_CONEXION, coordinador.estado.errorListado)
        assertFalse(coordinador.estado.cargandoListado)
    }
}

private class GatewayFalso : CotizacionesGateway {
    var llamado = false
    var token: String? = null
    var clienteId: String? = null
    var datos: Map<String, Any> = emptyMap()
    var respuesta: ResultadoApi<ResultadoCotizacion> = ResultadoApi.Exito(resultado())
    var clienteListado: String? = null
    var respuestaListado: ResultadoApi<List<ResultadoCotizacion>> =
        ResultadoApi.Exito(listOf(resultado()))

    override suspend fun listar(
        accessToken: String,
        clienteId: String
    ): ResultadoApi<List<ResultadoCotizacion>> {
        token = accessToken
        clienteListado = clienteId
        return respuestaListado
    }

    override suspend fun cotizar(
        accessToken: String,
        clienteId: String,
        ramo: RamoCotizacion,
        datosRiesgo: Map<String, Any>
    ): ResultadoApi<ResultadoCotizacion> {
        llamado = true
        token = accessToken
        this.clienteId = clienteId
        datos = datosRiesgo
        return respuesta
    }
}

private class SesionFalsa : SesionAutenticada {
    var token: String? = "access-1"
    var rechazos = 0

    override fun accessTokenVigente(): String? = token

    override fun sesionRechazada() {
        rechazos++
        token = null
    }
}

private fun resultado() = ResultadoCotizacion(
    cotizacionId = "COT-1",
    ramo = RamoCotizacion.VIAJE,
    estado = "VIGENTE",
    primaTotal = BigDecimal("21000.00"),
    moneda = "COP",
    coberturaPrincipal = CoberturaCotizacion(
        codigo = "ASISTENCIA_VIAJE",
        nombre = "Asistencia integral de viaje",
        sumaAsegurada = BigDecimal("20000000.00")
    ),
    vigenteHasta = "2026-10-22T12:00:00Z"
)
