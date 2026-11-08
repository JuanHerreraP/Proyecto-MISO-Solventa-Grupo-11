package com.example.solventa.domain.polizas

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.auth.RelojFalso
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
    private val cache = CachePolizasFalsa()
    private val reloj = RelojFalso()
    private val billetera = BilleteraCoordinator(gateway, sesion, cache, reloj)

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
    fun sinConexionMuestraLaUltimaBilleteraCacheadaSinErrorBloqueante() {
        val guardada = billeteraDe(resumen(id = "POL-CACHE"))
        ejecutar {
            cache.reemplazar(ClaveUsuarioCache("u-1"), guardada, emptyList(), 900_000L)
        }
        gateway.respuestaBilletera = ResultadoApi.SinConexion

        ejecutar { billetera.cargar() }

        assertEquals(guardada, billetera.estado.billetera)
        assertTrue(billetera.estado.usandoDatosLocales)
        assertTrue(billetera.estado.sinConexion)
        assertEquals(900_000L, billetera.estado.ultimaSincronizacionMs)
        assertFalse(billetera.estado.datosAntiguos)
        assertNull(billetera.estado.error)
    }

    @Test
    fun marcaComoAntiguosLosDatosCacheadosDeMasDeTreintaDias() {
        val diaMs = 24L * 60L * 60L * 1_000L
        reloj.ahora = 31L * diaMs
        ejecutar {
            cache.reemplazar(
                ClaveUsuarioCache("u-1"),
                billeteraDe(resumen()),
                emptyList(),
                0L
            )
        }
        gateway.respuestaBilletera = ResultadoApi.SinConexion

        ejecutar { billetera.cargar() }

        assertTrue(billetera.estado.datosAntiguos)
    }

    @Test
    fun nuncaMuestraLaCacheDeOtroUsuario() {
        ejecutar {
            cache.reemplazar(
                ClaveUsuarioCache("otro-usuario"),
                billeteraDe(resumen(id = "POL-AJENA")),
                emptyList(),
                1L
            )
        }
        gateway.respuestaBilletera = ResultadoApi.SinConexion

        ejecutar { billetera.cargar() }

        assertNull(billetera.estado.billetera)
        assertFalse(billetera.estado.usandoDatosLocales)
        assertEquals(MensajesBilletera.SIN_CONEXION, billetera.estado.error)
    }

    @Test
    fun muestraLaCacheAntesDeReemplazarlaConLaRespuestaRemota() {
        ejecutar {
            cache.reemplazar(
                ClaveUsuarioCache("u-1"),
                billeteraDe(resumen(id = "POL-CACHE")),
                emptyList(),
                1L
            )
        }
        gateway.respuestaBilletera = ResultadoApi.Exito(billeteraDe(resumen(id = "POL-REMOTA")))
        val estados = mutableListOf<EstadoBilletera>()
        billetera.observador = { estados += it }

        ejecutar { billetera.cargar() }

        assertTrue(estados.any { it.usandoDatosLocales && it.billetera?.polizas?.single()?.polizaId == "POL-CACHE" })
        assertEquals("POL-REMOTA", billetera.estado.billetera?.polizas?.single()?.polizaId)
        assertFalse(billetera.estado.usandoDatosLocales)
    }

    @Test
    fun unaRespuestaRemotaActualizaLaCacheDelUsuario() {
        val remota = billeteraDe(resumen(id = "POL-REMOTA"))
        gateway.respuestaBilletera = ResultadoApi.Exito(remota)

        ejecutar { billetera.cargar() }

        var guardada: BilleteraCacheada? = null
        ejecutar { guardada = cache.billetera(ClaveUsuarioCache("u-1")) }
        assertEquals(remota, guardada?.billetera)
        assertEquals(reloj.ahora, guardada?.metadatos?.sincronizadaEnMs)
    }

    @Test
    fun alRecrearElCoordinadorSinConexionRecuperaLaUltimaSincronizacion() {
        val guardada = billeteraDe(resumen(id = "POL-ANTES-DEL-REINICIO"))
        gateway.respuestaBilletera = ResultadoApi.Exito(guardada)
        ejecutar { billetera.cargar() }
        val gatewayTrasReinicio = PolizasGatewayFalso().apply {
            respuestaBilletera = ResultadoApi.SinConexion
        }
        val recreada = BilleteraCoordinator(gatewayTrasReinicio, sesion, cache, reloj)

        ejecutar { recreada.cargar() }

        assertEquals(guardada, recreada.estado.billetera)
        assertTrue(recreada.estado.usandoDatosLocales)
        assertTrue(recreada.estado.sinConexion)
        assertNull(recreada.estado.error)
    }

    @Test
    fun alRecuperarConexionReintentaYReemplazaLosDatosLocales() {
        val local = billeteraDe(resumen(id = "POL-LOCAL"))
        ejecutar {
            cache.reemplazar(ClaveUsuarioCache("u-1"), local, emptyList(), 1L)
        }
        gateway.respuestaBilletera = ResultadoApi.SinConexion
        ejecutar { billetera.cargar() }
        val remota = billeteraDe(resumen(id = "POL-REMOTA"))
        var intentos = 0
        val sincronizador = SincronizadorPolizas(
            sincronizar = {
                intentos++
                if (intentos == 2) gateway.respuestaBilletera = ResultadoApi.Exito(remota)
                billetera.sincronizarEnSegundoPlano()
            },
            alFalloPersistente = billetera::marcarFalloSincronizacionPersistente,
            esperar = {}
        )

        ejecutar { sincronizador.ejecutar() }

        assertEquals(2, intentos)
        assertEquals(remota, billetera.estado.billetera)
        assertFalse(billetera.estado.sinConexion)
        assertFalse(billetera.estado.usandoDatosLocales)
        assertFalse(billetera.estado.falloSincronizacionPersistente)
        var persistida: BilleteraCacheada? = null
        ejecutar { persistida = cache.billetera(ClaveUsuarioCache("u-1")) }
        assertEquals(remota, persistida?.billetera)
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
    fun sincronizacionAutomaticaNoInformaAntesDeAgotarLosReintentos() {
        ejecutar { billetera.cargar() }
        gateway.respuestaBilletera = ResultadoApi.Fallo(500, null, null)
        var resultado: ResultadoSincronizacion? = null

        ejecutar { resultado = billetera.sincronizarEnSegundoPlano() }

        assertEquals(ResultadoSincronizacion.REINTENTAR, resultado)
        assertNull(billetera.estado.error)
        assertFalse(billetera.estado.falloSincronizacionPersistente)
    }

    @Test
    fun marcaLaFallaPersistenteYSiguienteExitoLaLimpia() {
        billetera.marcarFalloSincronizacionPersistente()
        assertTrue(billetera.estado.falloSincronizacionPersistente)

        ejecutar { billetera.sincronizarEnSegundoPlano() }

        assertFalse(billetera.estado.falloSincronizacionPersistente)
        assertEquals(reloj.ahora, billetera.estado.ultimaSincronizacionMs)
    }

    @Test
    fun sincronizacionAutomaticaSinSesionNoMuestraSesionVencida() {
        sesion.token = null
        sesion.idUsuario = null
        var resultado: ResultadoSincronizacion? = null

        ejecutar { resultado = billetera.sincronizarEnSegundoPlano() }

        assertEquals(ResultadoSincronizacion.SIN_SESION, resultado)
        assertEquals(EstadoBilletera(), billetera.estado)
        assertEquals(0, sesion.rechazos)
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
    fun sinConexionMuestraElCertificadoCacheado() {
        ejecutar {
            cache.reemplazar(
                ClaveUsuarioCache("u-1"),
                billeteraDe(resumen()),
                listOf(certificado()),
                1L
            )
        }
        gateway.respuestaCertificado = ResultadoApi.SinConexion

        ejecutar { billetera.verCertificado("POL-1") }

        assertEquals(certificado(), billetera.estado.certificado)
        assertNull(billetera.estado.errorCertificado)
    }

    @Test
    fun unCertificadoRemotoQuedaDisponibleParaLaSiguienteConsultaOffline() {
        ejecutar { billetera.cargar() }
        ejecutar { billetera.verCertificado("POL-1") }
        billetera.cerrarCertificado()
        gateway.respuestaCertificado = ResultadoApi.SinConexion

        ejecutar { billetera.verCertificado("POL-1") }

        assertEquals(certificado(), billetera.estado.certificado)
        assertNull(billetera.estado.errorCertificado)
    }

    @Test
    fun unHistorialRemotoQuedaDisponibleParaLaSiguienteConsultaOffline() {
        val historial = historialEndosos()
        ejecutar { billetera.cargar() }
        gateway.respuestaHistorial = ResultadoApi.Exito(historial)

        ejecutar { billetera.verHistorialEndosos("POL-1") }

        assertEquals(listOf("POL-1"), gateway.historialesPedidos)
        assertEquals(historial, billetera.estado.historialEndosos)

        billetera.cerrarCertificado()
        gateway.respuestaHistorial = ResultadoApi.SinConexion
        ejecutar { billetera.verHistorialEndosos("POL-1") }

        assertEquals(historial, billetera.estado.historialEndosos)
        assertNull(billetera.estado.errorHistorial)
    }

    @Test
    fun sinConexionSinHistorialGuardadoInformaElProblema() {
        gateway.respuestaHistorial = ResultadoApi.SinConexion

        ejecutar { billetera.verHistorialEndosos("POL-1") }

        assertNull(billetera.estado.historialEndosos)
        assertEquals(MensajesBilletera.SIN_CONEXION, billetera.estado.errorHistorial)
    }

    @Test
    fun descargarDocumentoEntregaUnEventoConsumibleALaUi() {
        ejecutar { billetera.descargarDocumento("POL-1") }

        assertEquals(listOf("POL-1"), gateway.documentosPedidos)
        assertEquals("poliza.pdf", billetera.estado.documentoParaAbrir?.nombreArchivo)
        assertFalse(billetera.estado.descargandoDocumento)

        billetera.documentoAbierto(exito = true)
        assertNull(billetera.estado.documentoParaAbrir)
    }

    @Test
    fun documentoSinConexionInformaQueRequiereInternet() {
        gateway.respuestaDocumento = ResultadoApi.SinConexion

        ejecutar { billetera.descargarDocumento("POL-1") }

        assertNull(billetera.estado.documentoParaAbrir)
        assertEquals(MensajesBilletera.DOCUMENTO_REQUIERE_CONEXION, billetera.estado.mensaje)
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
    fun limpiarBorraElEstadoEnMemoria() {
        ejecutar { billetera.cargar() }
        ejecutar { billetera.verCertificado("POL-1") }

        billetera.limpiar()

        assertEquals(EstadoBilletera(), billetera.estado)
    }

    @Test
    fun cerrarSesionEliminaLaCacheCifrada() {
        ejecutar { billetera.cargar() }

        ejecutar { billetera.eliminarDatosLocales() }

        var guardada: BilleteraCacheada? = null
        ejecutar { guardada = cache.billetera(ClaveUsuarioCache("u-1")) }
        assertNull(guardada)
        assertEquals(EstadoBilletera(), billetera.estado)
    }

    @Test
    fun iniciarSinSesionNoBorraUnaCacheQuePuedeDesbloquearseDespues() {
        val guardada = billeteraDe(resumen(id = "POL-OFFLINE"))
        ejecutar {
            cache.reemplazar(ClaveUsuarioCache("u-1"), guardada, emptyList(), 1L)
        }

        billetera.limpiar()

        var recuperada: BilleteraCacheada? = null
        ejecutar { recuperada = cache.billetera(ClaveUsuarioCache("u-1")) }
        assertEquals(guardada, recuperada?.billetera)
    }

    @Test
    fun cambiarDeUsuarioEliminaLaCacheAnteriorAntesDeMostrarLaNueva() {
        ejecutar { billetera.cargar() }
        sesion.idUsuario = "u-2"
        sesion.token = "access-2"
        gateway.respuestaBilletera = ResultadoApi.Exito(billeteraDe(resumen(id = "POL-U2")))

        ejecutar { billetera.cargar() }

        var anterior: BilleteraCacheada? = null
        var nueva: BilleteraCacheada? = null
        ejecutar {
            anterior = cache.billetera(ClaveUsuarioCache("u-1"))
            nueva = cache.billetera(ClaveUsuarioCache("u-2"))
        }
        assertNull(anterior)
        assertEquals("POL-U2", nueva?.billetera?.polizas?.single()?.polizaId)
        assertEquals("POL-U2", billetera.estado.billetera?.polizas?.single()?.polizaId)
    }

    @Test
    fun respuestaTardiaDelUsuarioAnteriorNoSeMuestraNiSePersiste() {
        ejecutar {
            cache.reemplazar(
                ClaveUsuarioCache("u-1"),
                billeteraDe(resumen(id = "POL-U1-CACHE")),
                emptyList(),
                1L
            )
        }
        lateinit var coordinador: BilleteraCoordinator
        val gatewayConCambio = object : PolizasGateway by gateway {
            override suspend fun billetera(accessToken: String): ResultadoApi<Billetera> {
                sesion.idUsuario = "u-2"
                sesion.token = "access-2"
                coordinador.registrarUsuario("u-2")
                return ResultadoApi.Exito(billeteraDe(resumen(id = "POL-U1-TARDIA")))
            }
        }
        coordinador = BilleteraCoordinator(gatewayConCambio, sesion, cache, reloj)

        ejecutar { coordinador.cargar() }

        assertEquals(EstadoBilletera(), coordinador.estado)
        var anterior: BilleteraCacheada? = null
        var nueva: BilleteraCacheada? = null
        ejecutar {
            anterior = cache.billetera(ClaveUsuarioCache("u-1"))
            nueva = cache.billetera(ClaveUsuarioCache("u-2"))
        }
        assertNull(anterior)
        assertNull(nueva)
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
        coordinadorLento = BilleteraCoordinator(lento, sesion, cache, reloj)

        ejecutar { coordinadorLento.cargar() }

        assertEquals(EstadoBilletera(), coordinadorLento.estado)
    }

    private lateinit var coordinadorLento: BilleteraCoordinator
}
