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

    @Test
    fun elPagoAprobadoTraeSuComprobanteSinMostrarloComoDialogo() = runBlocking {
        coordinador.pagar(solicitudTarjeta())

        assertEquals(listOf("PAG-1"), gateway.comprobantesPedidos)
        assertEquals(comprobante(), coordinador.estado.comprobante)
        assertFalse(coordinador.estado.comprobanteVisible)
    }

    @Test
    fun sinComprobanteElPagoAprobadoSigueSiendoValido() = runBlocking {
        gateway.respuestaComprobante = ResultadoApi.Fallo(500, null, null)

        coordinador.pagar(solicitudTarjeta())

        assertEquals(EstadoPago.APROBADO, coordinador.estado.pago?.estado)
        assertNull(coordinador.estado.comprobante)
        assertNull(coordinador.estado.error)
    }

    @Test
    fun unPagoRechazadoNoPideComprobante() = runBlocking {
        gateway.respuesta = ResultadoApi.Exito(pago().copy(estado = EstadoPago.RECHAZADO))

        coordinador.pagar(solicitudTarjeta())

        assertEquals(emptyList<String>(), gateway.comprobantesPedidos)
        assertNull(coordinador.estado.comprobante)
    }

    @Test
    fun alConsultarUnPagoAprobadoTambienSeCargaSuComprobante() = runBlocking {
        coordinador.consultar("PAG-1")

        assertEquals(comprobante(), coordinador.estado.comprobante)
    }

    @Test
    fun cargaLasPrimasPendientes() = runBlocking {
        gateway.respuestaPendientes = ResultadoApi.Exito(listOf(prima()))

        coordinador.cargarPendientes()

        assertEquals(listOf(prima()), coordinador.estado.pendientes)
        assertFalse(coordinador.estado.cargandoPendientes)
        assertNull(coordinador.estado.errorPendientes)
    }

    @Test
    fun siFallanLasPendientesMuestraUnMensajeSegunElError() = runBlocking {
        gateway.respuestaPendientes = ResultadoApi.Fallo(500, null, null)
        coordinador.cargarPendientes()
        assertEquals(MensajesPagos.PENDIENTES_NO_DISPONIBLES, coordinador.estado.errorPendientes)

        gateway.respuestaPendientes = ResultadoApi.SinConexion
        coordinador.cargarPendientes()
        assertEquals(MensajesPagos.SIN_CONEXION, coordinador.estado.errorPendientes)
    }

    @Test
    fun unTokenRechazadoAlCargarPendientesCierraLaSesion() = runBlocking {
        gateway.respuestaPendientes = ResultadoApi.Fallo(401, null, null)

        coordinador.cargarPendientes()

        assertEquals(1, sesion.rechazos)
    }

    @Test
    fun verElComprobanteLoMuestraYSePuedeCerrar() = runBlocking {
        coordinador.verComprobante("PAG-1")

        assertEquals(comprobante(), coordinador.estado.comprobante)
        assertEquals(true, coordinador.estado.comprobanteVisible)
        assertFalse(coordinador.estado.cargandoComprobante)

        coordinador.cerrarComprobante()

        assertFalse(coordinador.estado.comprobanteVisible)
    }

    @Test
    fun siNoSePuedeConsultarElComprobanteInformaElError() = runBlocking {
        gateway.respuestaComprobante = ResultadoApi.Fallo(409, "PAGO_SIN_COMPROBANTE", null)
        coordinador.verComprobante("PAG-1")
        assertEquals(MensajesPagos.COMPROBANTE_NO_DISPONIBLE, coordinador.estado.errorComprobante)

        gateway.respuestaComprobante = ResultadoApi.SinConexion
        coordinador.verComprobante("PAG-1")
        assertEquals(MensajesPagos.SIN_CONEXION, coordinador.estado.errorComprobante)
        assertNull(coordinador.estado.comprobante)
    }

    @Test
    fun unTokenRechazadoAlVerElComprobanteCierraLaSesion() = runBlocking {
        gateway.respuestaComprobante = ResultadoApi.Fallo(401, null, null)

        coordinador.verComprobante("PAG-1")

        assertEquals(1, sesion.rechazos)
    }

    @Test
    fun limpiarTambienDescartaPendientesYComprobante() = runBlocking {
        gateway.respuestaPendientes = ResultadoApi.Exito(listOf(prima()))
        coordinador.cargarPendientes()
        coordinador.verComprobante("PAG-1")

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

    var respuestaPendientes: ResultadoApi<List<PrimaPendiente>> = ResultadoApi.Exito(emptyList())
    var respuestaComprobante: ResultadoApi<ComprobantePago> = ResultadoApi.Exito(comprobante())
    val comprobantesPedidos = mutableListOf<String>()

    override suspend fun pendientes(accessToken: String): ResultadoApi<List<PrimaPendiente>> {
        token = accessToken
        return respuestaPendientes
    }

    override suspend fun comprobante(
        accessToken: String,
        pagoId: String
    ): ResultadoApi<ComprobantePago> {
        token = accessToken
        comprobantesPedidos += pagoId
        return respuestaComprobante
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

private fun comprobante() = ComprobantePago(
    numero = "CP-20261210-ABCD1234",
    pagoId = "PAG-1",
    concepto = ConceptoPago.COMPRA,
    descripcion = "Prima de Seguro de viaje",
    polizaId = null,
    numeroPoliza = null,
    monto = BigDecimal("45000.00"),
    moneda = "COP",
    metodo = MetodoPago.TARJETA,
    referenciaPasarela = "PSP-1",
    pagadoEn = "2026-12-10T15:00:00Z"
)

private fun prima() = PrimaPendiente(
    tipo = TipoPrimaPendiente.COTIZACION,
    referenciaId = "COT-9",
    cotizacionId = "COT-9",
    polizaId = null,
    numeroPoliza = null,
    nombreRamo = "Microseguro de vida",
    monto = BigDecimal("89000.00"),
    moneda = "COP",
    fechaLimite = "2026-12-17T15:00:00Z",
    mensaje = null
)
