package com.example.solventa.domain.polizas

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.auth.ejecutar
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** HU07 (BPM-31): reglas de la billetera, sin Android. */
class BilleteraCoordinatorTest {
    private val gateway = PolizasGatewayFalso()
    private val sesion = SesionFalsa()
    private val billetera = BilleteraCoordinator(gateway, sesion)

    @Test
    fun cargaLaBilleteraConElTokenDeLaSesion() {
        ejecutar { billetera.cargar() }

        assertEquals(listOf("access-1"), gateway.tokensUsados)
        assertEquals(billeteraDe(resumen()), billetera.estado.billetera)
        assertFalse(billetera.estado.cargando)
        assertNull(billetera.estado.error)
    }

    @Test
    fun separaVigentesDeInactivas() {
        gateway.respuestaBilletera = ResultadoApi.Exito(
            billeteraDe(
                resumen(id = "A"),
                resumen(id = "B", estado = EstadoPoliza.VENCIDA),
                resumen(id = "C", estado = EstadoPoliza.CANCELADA)
            )
        )

        ejecutar { billetera.cargar() }

        val cargada = checkNotNull(billetera.estado.billetera)
        assertEquals(listOf("A"), cargada.vigentes.map { it.polizaId })
        assertEquals(listOf("B", "C"), cargada.inactivas.map { it.polizaId })
    }

    @Test
    fun sinConexionMuestraElErrorYPermiteReintentar() {
        gateway.respuestaBilletera = ResultadoApi.SinConexion

        ejecutar { billetera.cargar() }
        assertEquals(MensajesBilletera.SIN_CONEXION, billetera.estado.error)

        gateway.respuestaBilletera = ResultadoApi.Exito(billeteraDe())
        ejecutar { billetera.cargar() }
        assertNull(billetera.estado.error)
        assertTrue(checkNotNull(billetera.estado.billetera).vacia)
    }

    @Test
    fun unErrorDelServidorConservaLoQueYaSeHabiaCargado() {
        ejecutar { billetera.cargar() }
        gateway.respuestaBilletera = ResultadoApi.Fallo(500, null, null)

        ejecutar { billetera.cargar() }

        assertEquals(MensajesBilletera.ERROR_GENERICO, billetera.estado.error)
        assertEquals(billeteraDe(resumen()), billetera.estado.billetera)
    }

    @Test
    fun siElBackendRechazaElTokenSeCierraLaSesionYSeBorraLoCargado() {
        ejecutar { billetera.cargar() }
        gateway.respuestaBilletera = ResultadoApi.Fallo(401, "TOKEN_EXPIRED", null)

        ejecutar { billetera.cargar() }

        assertEquals(1, sesion.rechazos)
        assertNull(billetera.estado.billetera)
        assertEquals(MensajesBilletera.SESION_VENCIDA, billetera.estado.mensaje)
    }

    @Test
    fun sinSesionNoLlamaAlBackend() {
        sesion.token = null

        ejecutar { billetera.cargar() }

        assertTrue(gateway.tokensUsados.isEmpty())
        assertEquals(1, sesion.rechazos)
    }

    @Test
    fun muestraElCertificadoConSuQr() {
        ejecutar { billetera.verCertificado("POL-1") }

        assertEquals(listOf("POL-1"), gateway.certificadosPedidos)
        assertEquals(certificado(), billetera.estado.certificado)
        assertFalse(billetera.estado.cargandoCertificado)
    }

    @Test
    fun unaPolizaAjenaSeMuestraComoNoEncontrada() {
        gateway.respuestaCertificado = ResultadoApi.Fallo(404, "POLIZA_NO_ENCONTRADA", null)

        ejecutar { billetera.verCertificado("POL-DE-OTRO") }

        assertNull(billetera.estado.certificado)
        assertEquals(MensajesBilletera.POLIZA_NO_ENCONTRADA, billetera.estado.errorCertificado)
    }

    @Test
    fun alAbrirOtraPolizaNoSeMuestraElCertificadoAnterior() {
        ejecutar { billetera.verCertificado("POL-1") }
        gateway.respuestaCertificado = ResultadoApi.SinConexion

        ejecutar { billetera.verCertificado("POL-2") }

        assertNull(billetera.estado.certificado)
        assertEquals(MensajesBilletera.SIN_CONEXION, billetera.estado.errorCertificado)
    }

    @Test
    fun compartirEntregaElEnlaceUnaSolaVez() {
        ejecutar { billetera.compartir("POL-1") }

        assertEquals(listOf("POL-1"), gateway.compartidos)
        assertEquals(ENLACE, billetera.estado.enlaceParaCompartir)

        billetera.enlaceCompartido()
        assertNull(billetera.estado.enlaceParaCompartir)
    }

    @Test
    fun siNoSePuedeCompartirSeAvisa() {
        gateway.respuestaCompartir = ResultadoApi.Fallo(500, null, null)

        ejecutar { billetera.compartir("POL-1") }

        assertNull(billetera.estado.enlaceParaCompartir)
        assertEquals(MensajesBilletera.COMPARTIR_FALLIDO, billetera.estado.mensaje)
        assertFalse(billetera.estado.compartiendo)

        billetera.consumirMensaje()
        assertNull(billetera.estado.mensaje)
    }

    @Test
    fun cerrarElCertificadoDescartaSuEstado() {
        ejecutar { billetera.verCertificado("POL-1") }
        ejecutar { billetera.compartir("POL-1") }

        billetera.cerrarCertificado()

        assertNull(billetera.estado.certificado)
        assertNull(billetera.estado.enlaceParaCompartir)
    }

    @Test
    fun limpiarBorraTodoParaElSiguienteUsuario() {
        ejecutar { billetera.cargar() }
        ejecutar { billetera.verCertificado("POL-1") }

        billetera.limpiar()

        assertEquals(EstadoBilletera(), billetera.estado)
    }

    @Test
    fun elObservadorRecibeElEstadoActualAlRegistrarse() {
        val recibidos = mutableListOf<EstadoBilletera>()
        billetera.observador = { recibidos += it }

        ejecutar { billetera.cargar() }

        assertEquals(EstadoBilletera(), recibidos.first())
        assertEquals(billeteraDe(resumen()), recibidos.last().billetera)
    }

    @Test
    fun unaRespuestaQueLlegaDespuesDeCerrarSesionSeIgnora() {
        val lento = object : PolizasGateway by gateway {
            override suspend fun billetera(accessToken: String): ResultadoApi<Billetera> {
                coordinadorLento.limpiar()
                return ResultadoApi.Exito(billeteraDe(resumen()))
            }
        }
        coordinadorLento = BilleteraCoordinator(lento, sesion)

        ejecutar { coordinadorLento.cargar() }

        assertEquals(EstadoBilletera(), coordinadorLento.estado)
    }

    private lateinit var coordinadorLento: BilleteraCoordinator
}
