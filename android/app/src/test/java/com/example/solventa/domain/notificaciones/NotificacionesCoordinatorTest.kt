package com.example.solventa.domain.notificaciones

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.SesionAutenticada
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GatewayNotificacionesFalso : NotificacionesGateway {
    var bandeja: ResultadoApi<Bandeja> = ResultadoApi.Exito(Bandeja(emptyList(), 0))
    var conteo: ResultadoApi<Int> = ResultadoApi.Exito(0)
    var lectura: ResultadoApi<Int> = ResultadoApi.Exito(0)
    var registro: ResultadoApi<Unit> = ResultadoApi.Exito(Unit)
    var baja: ResultadoApi<Unit> = ResultadoApi.Exito(Unit)
    var preferencia: ResultadoApi<Boolean> = ResultadoApi.Exito(true)
    var cambio: ResultadoApi<Boolean>? = null

    val tokensUsados = mutableListOf<String>()
    val registrados = mutableListOf<String>()
    val bajas = mutableListOf<String>()
    val leidas = mutableListOf<String>()
    val preferenciasEnviadas = mutableListOf<Boolean>()

    override suspend fun listar(accessToken: String): ResultadoApi<Bandeja> {
        tokensUsados += accessToken
        return bandeja
    }

    override suspend fun contarNoLeidas(accessToken: String): ResultadoApi<Int> = conteo

    override suspend fun marcarLeida(accessToken: String, notificacionId: String): ResultadoApi<Int> {
        leidas += notificacionId
        return lectura
    }

    override suspend fun registrarDispositivo(accessToken: String, tokenPush: String): ResultadoApi<Unit> {
        registrados += tokenPush
        return registro
    }

    override suspend fun darDeBajaDispositivo(accessToken: String, tokenPush: String): ResultadoApi<Unit> {
        bajas += tokenPush
        return baja
    }

    override suspend fun obtenerPreferencia(accessToken: String): ResultadoApi<Boolean> = preferencia

    override suspend fun cambiarPreferencia(
        accessToken: String,
        pushHabilitado: Boolean
    ): ResultadoApi<Boolean> {
        preferenciasEnviadas += pushHabilitado
        return cambio ?: ResultadoApi.Exito(pushHabilitado)
    }
}

class SesionNotificacionesFalsa(var token: String? = "access-1") : SesionAutenticada {
    var rechazos = 0

    override fun accessTokenVigente(): String? = token

    override fun sesionRechazada() {
        rechazos++
        token = null
    }
}

class ProveedorTokenFalso(var token: String? = "tok-1") : ProveedorTokenPush {
    var olvidos = 0

    override suspend fun token(): String? = token

    override suspend fun olvidar() {
        olvidos++
        token = null
    }
}

fun notificacion(
    id: String,
    tipo: TipoNotificacion = TipoNotificacion.ESTADO_SINIESTRO,
    datos: Map<String, String> = mapOf(CLAVE_SINIESTRO_ID to "SIN-1"),
    leida: Boolean = false
) = Notificacion(id, tipo, "Título $id", "Cuerpo $id", datos, "2026-12-10T15:00:00Z", leida)

class NotificacionesCoordinatorTest {

    private val gateway = GatewayNotificacionesFalso()
    private val sesion = SesionNotificacionesFalsa()
    private val proveedor = ProveedorTokenFalso()

    private fun coordinador(conProveedor: Boolean = true) = NotificacionesCoordinator(
        gateway, sesion, if (conProveedor) proveedor else SinProveedorPush
    )

    @Test
    fun cargarGuardaLaBandejaYLaInsignia() = runBlocking {
        gateway.bandeja = ResultadoApi.Exito(
            Bandeja(listOf(notificacion("N-1"), notificacion("N-2", leida = true)), noLeidas = 1)
        )
        val c = coordinador()

        c.cargar()

        assertFalse(c.estado.cargando)
        assertNull(c.estado.error)
        assertEquals(2, c.estado.bandeja?.notificaciones?.size)
        assertEquals(1, c.estado.noLeidas)
        assertEquals(listOf("access-1"), gateway.tokensUsados)
    }

    @Test
    fun cargarConErrorDelBackendInformaSinPerderLaInsignia() = runBlocking {
        gateway.bandeja = ResultadoApi.Fallo(500, null, null)
        val c = coordinador()

        c.cargar()

        assertEquals(MensajesNotificaciones.ERROR_GENERICO, c.estado.error)
        assertNull(c.estado.bandeja)
        assertFalse(c.estado.cargando)
    }

    @Test
    fun cargarSinConexionMuestraElMensajeDeRed() = runBlocking {
        gateway.bandeja = ResultadoApi.SinConexion
        val c = coordinador()

        c.cargar()

        assertEquals(MensajesNotificaciones.SIN_CONEXION, c.estado.error)
    }

    @Test
    fun unTokenRechazadoCierraLaSesion() = runBlocking {
        gateway.bandeja = ResultadoApi.Fallo(401, "TOKEN_EXPIRED", null)
        val c = coordinador()

        c.cargar()

        assertEquals(1, sesion.rechazos)
        assertEquals(MensajesNotificaciones.SESION_VENCIDA, c.estado.error)
    }

    @Test
    fun sinTokenCierraLaSesionAlCargar() = runBlocking {
        sesion.token = null
        val c = coordinador()

        c.cargar()

        assertEquals(1, sesion.rechazos)
        assertTrue(gateway.tokensUsados.isEmpty())
    }

    @Test
    fun laInsigniaSeActualizaSinTocarLaBandeja() = runBlocking {
        gateway.conteo = ResultadoApi.Exito(4)
        val c = coordinador()

        c.actualizarInsignia()

        assertEquals(4, c.estado.noLeidas)
        assertNull(c.estado.bandeja)
    }

    @Test
    fun unFalloAlActualizarLaInsigniaNoMolesta() = runBlocking {
        gateway.conteo = ResultadoApi.SinConexion
        val c = coordinador()

        c.actualizarInsignia()

        assertNull(c.estado.error)
        assertEquals(0, c.estado.noLeidas)
    }

    @Test
    fun marcarLeidaActualizaLaNotificacionYLaInsignia() = runBlocking {
        gateway.bandeja = ResultadoApi.Exito(
            Bandeja(listOf(notificacion("N-1"), notificacion("N-2")), noLeidas = 2)
        )
        gateway.lectura = ResultadoApi.Exito(1)
        val c = coordinador()
        c.cargar()

        c.marcarLeida("N-1")

        assertEquals(listOf("N-1"), gateway.leidas)
        assertEquals(1, c.estado.noLeidas)
        assertEquals(listOf(true, false), c.estado.bandeja?.notificaciones?.map { it.leida })
        assertEquals(1, c.estado.bandeja?.noLeidas)
    }

    @Test
    fun marcarLeidaQueFallaDejaTodoComoEstaba() = runBlocking {
        gateway.bandeja = ResultadoApi.Exito(Bandeja(listOf(notificacion("N-1")), noLeidas = 1))
        gateway.lectura = ResultadoApi.SinConexion
        val c = coordinador()
        c.cargar()

        c.marcarLeida("N-1")

        assertEquals(1, c.estado.noLeidas)
        assertFalse(c.estado.bandeja!!.notificaciones.first().leida)
    }

    @Test
    fun marcarLeidaConToken401CierraLaSesion() = runBlocking {
        gateway.lectura = ResultadoApi.Fallo(401, null, null)
        val c = coordinador()

        c.marcarLeida("N-1")

        assertEquals(1, sesion.rechazos)
    }

    // --- Preferencia --------------------------------------------------------------------

    @Test
    fun cargarPreferenciaGuardaElValorDelBackend() = runBlocking {
        gateway.preferencia = ResultadoApi.Exito(false)
        val c = coordinador()

        c.cargarPreferencia()

        assertEquals(false, c.estado.pushHabilitado)
    }

    @Test
    fun cambiarPreferenciaLaGuarda() = runBlocking {
        val c = coordinador()

        c.cambiarPreferencia(false)

        assertEquals(listOf(false), gateway.preferenciasEnviadas)
        assertEquals(false, c.estado.pushHabilitado)
        assertFalse(c.estado.cambiandoPreferencia)
        assertNull(c.estado.errorPreferencia)
    }

    @Test
    fun siNoSePuedeGuardarElInterruptorVuelveAComoEstaba() = runBlocking {
        gateway.preferencia = ResultadoApi.Exito(true)
        val c = coordinador()
        c.cargarPreferencia()
        gateway.cambio = ResultadoApi.Fallo(500, null, null)

        c.cambiarPreferencia(false)

        assertEquals(true, c.estado.pushHabilitado)
        assertEquals(MensajesNotificaciones.PREFERENCIA_NO_GUARDADA, c.estado.errorPreferencia)
        assertFalse(c.estado.cambiandoPreferencia)
    }

    @Test
    fun sinConexionAlCambiarLaPreferenciaTambienSeRevierte() = runBlocking {
        gateway.preferencia = ResultadoApi.Exito(true)
        val c = coordinador()
        c.cargarPreferencia()
        gateway.cambio = ResultadoApi.SinConexion

        c.cambiarPreferencia(false)

        assertEquals(true, c.estado.pushHabilitado)
        assertEquals(MensajesNotificaciones.SIN_CONEXION, c.estado.errorPreferencia)
    }

    // --- Dispositivo --------------------------------------------------------------------

    @Test
    fun registraElTokenDelProveedor() = runBlocking {
        val c = coordinador()

        assertTrue(c.registrarDispositivo())

        assertEquals(listOf("tok-1"), gateway.registrados)
    }

    @Test
    fun sinProveedorNoRegistraNada() = runBlocking {
        val c = coordinador(conProveedor = false)

        assertFalse(c.registrarDispositivo())

        assertTrue(gateway.registrados.isEmpty())
    }

    @Test
    fun unRegistroQueFallaNoEsUnErrorParaElCliente() = runBlocking {
        gateway.registro = ResultadoApi.SinConexion
        val c = coordinador()

        assertFalse(c.registrarDispositivo())

        assertNull(c.estado.error)
    }

    @Test
    fun registrarElTokenConToken401CierraLaSesion() = runBlocking {
        gateway.registro = ResultadoApi.Fallo(401, null, null)
        val c = coordinador()

        assertFalse(c.registrarToken("tok-9"))

        assertEquals(1, sesion.rechazos)
    }

    @Test
    fun registrarTokenSinSesionNoLlamaAlBackend() = runBlocking {
        sesion.token = null
        val c = coordinador()

        assertFalse(c.registrarToken("tok-9"))

        assertTrue(gateway.registrados.isEmpty())
    }

    @Test
    fun alCerrarSesionSeDaDeBajaElTokenRegistradoYSeOlvida() = runBlocking {
        val c = coordinador()
        c.registrarToken("tok-9")

        c.darDeBajaDispositivo()

        assertEquals(listOf("tok-9"), gateway.bajas)
        assertEquals(1, proveedor.olvidos)
    }

    @Test
    fun sinRegistroPrevioLaBajaUsaElTokenDelProveedor() = runBlocking {
        val c = coordinador()

        c.darDeBajaDispositivo()

        assertEquals(listOf("tok-1"), gateway.bajas)
    }

    @Test
    fun sinTokenNiSesionLaBajaNoLlamaAlBackend() = runBlocking {
        sesion.token = null
        val c = coordinador(conProveedor = false)

        c.darDeBajaDispositivo()

        assertTrue(gateway.bajas.isEmpty())
    }

    @Test
    fun limpiarDescartaLoCargadoYIgnoraRespuestasEnVuelo() = runBlocking {
        gateway.bandeja = ResultadoApi.Exito(Bandeja(listOf(notificacion("N-1")), 1))
        val c = coordinador()
        c.cargar()

        c.limpiar()

        assertEquals(EstadoNotificaciones(), c.estado)
    }

    @Test
    fun elObservadorRecibeElEstadoActualYLosCambios() = runBlocking {
        val c = coordinador()
        val vistos = mutableListOf<EstadoNotificaciones>()

        c.observador = { vistos += it }
        c.actualizarInsignia()

        assertEquals(EstadoNotificaciones(), vistos.first())
        assertTrue(vistos.size >= 1)
    }
}

class DestinoNotificacionTest {

    @Test
    fun elVencimientoAbreLaRenovacionDeLaPoliza() {
        assertEquals(
            DestinoNotificacion.Renovacion("POL-1"),
            destinoDe(TipoNotificacion.VENCIMIENTO_POLIZA, mapOf(CLAVE_POLIZA_ID to "POL-1"))
        )
    }

    @Test
    fun elPagoYElCambioDeEstadoAbrenElDetalleDelSiniestro() {
        val datos = mapOf(CLAVE_SINIESTRO_ID to "SIN-1")
        assertEquals(
            DestinoNotificacion.DetalleSiniestro("SIN-1"),
            destinoDe(TipoNotificacion.PAGO_PARAMETRICO, datos)
        )
        assertEquals(
            DestinoNotificacion.DetalleSiniestro("SIN-1"),
            destinoDe(TipoNotificacion.ESTADO_SINIESTRO, datos)
        )
    }

    @Test
    fun sinElIdentificadorNecesarioLlevaALaBandeja() {
        assertEquals(
            DestinoNotificacion.Bandeja,
            destinoDe(TipoNotificacion.VENCIMIENTO_POLIZA, emptyMap())
        )
        assertEquals(
            DestinoNotificacion.Bandeja,
            destinoDe(TipoNotificacion.ESTADO_SINIESTRO, mapOf(CLAVE_SINIESTRO_ID to " "))
        )
        assertEquals(DestinoNotificacion.Bandeja, destinoDe(null, emptyMap()))
    }

    @Test
    fun elCodigoDesconocidoNoEsUnTipo() {
        assertNull(TipoNotificacion.desdeCodigo("OTRO"))
        assertNull(TipoNotificacion.desdeCodigo(null))
        assertEquals(TipoNotificacion.PAGO_PARAMETRICO, TipoNotificacion.desdeCodigo("PAGO_PARAMETRICO"))
    }

    @Test
    fun laBandejaVaciaSeReconoce() {
        assertTrue(Bandeja(emptyList(), 0).vacia)
        assertFalse(Bandeja(listOf(notificacion("N-1")), 1).vacia)
    }
}
