package com.example.solventa.domain.pagos

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.SesionAutenticada
import java.math.BigDecimal
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Test

class PagosCoordinatorTest {
    private val gateway = GatewayFalso()
    private val sesion = SesionFalsa()
    private var contador = 0
    private val coordinador = PagosCoordinator(gateway, sesion, generarLlave = { "llave-${contador++}" })

    @Test
    fun pagoAprobadoConservaElResultadoYUsaLaLlaveDeIdempotencia() = runBlocking {
        coordinador.pagar(solicitudTarjeta())

        assertEquals("access-1", gateway.token)
        assertEquals("llave-0", gateway.llave)
        assertEquals(EstadoPago.APROBADO, coordinador.estado.pago?.estado)
        assertFalse(coordinador.estado.procesando)
        assertNull(coordinador.estado.error)
    }

    @Test
    fun reintentarConLaMismaLlaveMientrasNoSePrepareNuevoIntento() = runBlocking {
        coordinador.pagar(solicitudTarjeta())
        val primera = gateway.llave
        coordinador.pagar(solicitudTarjeta())

        assertEquals(primera, gateway.llave)
    }

    @Test
    fun prepararReintentoGeneraUnaLlaveNueva() = runBlocking {
        coordinador.pagar(solicitudTarjeta())
        val primera = gateway.llave

        coordinador.prepararReintento()
        coordinador.pagar(solicitudTarjeta())

        assertNotEquals(primera, gateway.llave)
        assertNull(coordinador.estado.error)
    }

    @Test
    fun cotizacionNoVigenteMuestraMensajeDeConflicto() = runBlocking {
        gateway.respuesta = ResultadoApi.Fallo(409, "COTIZACION_NO_VIGENTE", null)

        coordinador.pagar(solicitudTarjeta())

        assertEquals(MensajesPagos.COTIZACION_NO_VIGENTE, coordinador.estado.error)
    }

    @Test
    fun tokenRechazadoCierraLaSesion() = runBlocking {
        gateway.respuesta = ResultadoApi.Fallo(401, "TOKEN_EXPIRED", null)

        coordinador.pagar(solicitudTarjeta())

        assertEquals(1, sesion.rechazos)
        assertEquals(MensajesPagos.SESION_VENCIDA, coordinador.estado.error)
    }

    @Test
    fun sinConexionMuestraMensajeDeRed() = runBlocking {
        gateway.respuesta = ResultadoApi.SinConexion

        coordinador.pagar(solicitudTarjeta())

        assertEquals(MensajesPagos.SIN_CONEXION, coordinador.estado.error)
    }

    @Test
    fun limpiarDescartaElEstado() = runBlocking {
        coordinador.pagar(solicitudTarjeta())

        coordinador.limpiar()

        assertEquals(EstadoPagos(), coordinador.estado)
    }

    private fun solicitudTarjeta() = SolicitudPago(
        cotizacionId = "COT-1",
        metodo = MetodoPago.TARJETA,
        tokenTarjeta = "tok_visa_123456"
    )
}

private class GatewayFalso : PagosGateway {
    var token: String? = null
    var llave: String? = null
    var respuesta: ResultadoApi<Pago> = ResultadoApi.Exito(pago())

    override suspend fun pagar(
        accessToken: String,
        idempotencyKey: String,
        solicitud: SolicitudPago
    ): ResultadoApi<Pago> {
        token = accessToken
        llave = idempotencyKey
        return respuesta
    }

    override suspend fun consultar(accessToken: String, pagoId: String): ResultadoApi<Pago> {
        token = accessToken
        return respuesta
    }

    override suspend fun listar(accessToken: String): ResultadoApi<List<Pago>> {
        token = accessToken
        return ResultadoApi.Exito(listOf(pago()))
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

private fun pago() = Pago(
    pagoId = "PAG-1",
    cotizacionId = "COT-1",
    metodo = MetodoPago.TARJETA,
    monto = BigDecimal("45000.00"),
    moneda = "COP",
    estado = EstadoPago.APROBADO
)
