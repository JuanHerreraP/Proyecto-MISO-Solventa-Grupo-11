package com.example.solventa.domain.siniestros

import com.example.solventa.domain.auth.ResultadoApi
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** HU04: reporte con evidencias, borrador sin conexión y reintento sin duplicar. */
class SiniestrosEvidenciasTest {

    private val gateway = SiniestrosGatewayFalso()
    private val borradores = BorradoresFalsos()
    private val sesion = SesionSiniestrosFalsa()
    private var usuario: String? = "USR-1"
    private var consecutivo = 0

    private val coordinador = SiniestrosCoordinator(
        gateway = gateway,
        sesion = sesion,
        borradores = borradores,
        usuarioActual = { usuario },
        reloj = { 1_000L },
        generarId = { "BORRADOR-${++consecutivo}" }
    )

    private fun solicitudHu04() = solicitud().copy(tipoSiniestro = TipoSiniestro.DANO_MATERIAL)

    private suspend fun conEvidencias(vararg ids: String) {
        ids.forEach { coordinador.agregarEvidencia(EvidenciaImportada.Lista(evidencia(id = it))) }
    }

    @Test
    fun registraElSiniestroSubeLasEvidenciasYEliminaElBorrador() = runBlocking {
        conEvidencias("E1", "E2")

        coordinador.registrar(solicitudHu04())

        val estado = coordinador.estado
        assertTrue(estado.registroExitoso)
        assertFalse(estado.registrando)
        assertNull(estado.errorFormulario)
        assertNull(estado.borrador)
        assertNull(borradores.porUsuario["USR-1"])
        // El siniestro se registró con el id del borrador como Idempotency-Key.
        assertEquals("BORRADOR-1", gateway.solicitudes.single().claveIdempotencia)
        assertEquals(TipoSiniestro.DANO_MATERIAL, gateway.solicitudes.single().tipoSiniestro)
        assertEquals(listOf("SIN-NUEVO" to "E1", "SIN-NUEVO" to "E2"), gateway.evidenciasSubidas)
        // Se recargó la lista después de registrar.
        assertNotNull(estado.siniestros)
    }

    @Test
    fun sinEvidenciasTambienRegistraConBorrador() = runBlocking {
        coordinador.registrar(solicitudHu04())

        assertTrue(coordinador.estado.registroExitoso)
        assertEquals("BORRADOR-1", gateway.solicitudes.single().claveIdempotencia)
        assertTrue(gateway.evidenciasSubidas.isEmpty())
    }

    @Test
    fun sinConexionAlRegistrarGuardaElBorradorConLosDatos() = runBlocking {
        conEvidencias("E1")
        gateway.respuestaRegistro = ResultadoApi.SinConexion

        coordinador.registrar(solicitudHu04())

        val estado = coordinador.estado
        assertEquals(MensajesSiniestros.BORRADOR_GUARDADO, estado.errorFormulario)
        assertFalse(estado.registrando)
        assertFalse(estado.registroExitoso)
        val guardado = borradores.porUsuario.getValue("USR-1")
        assertEquals("POL-1", guardado.polizaId)
        assertEquals("El vuelo fue cancelado y hubo gastos adicionales.", guardado.descripcion)
        assertEquals(TipoSiniestro.DANO_MATERIAL, guardado.tipoSiniestro)
        assertNull(guardado.siniestroId)
        assertEquals(listOf("E1"), guardado.pendientes.map { it.id })
        assertTrue(gateway.evidenciasSubidas.isEmpty())
    }

    @Test
    fun elReintentoUsaLaMismaClaveYNoDuplicaElSiniestro() = runBlocking {
        gateway.respuestaRegistro = ResultadoApi.SinConexion
        coordinador.registrar(solicitudHu04())

        gateway.respuestaRegistro = ResultadoApi.Exito(siniestro(id = "SIN-NUEVO"))
        coordinador.registrar(solicitudHu04())

        assertEquals(listOf("BORRADOR-1", "BORRADOR-1"), gateway.solicitudes.map { it.claveIdempotencia })
        assertTrue(coordinador.estado.registroExitoso)
    }

    @Test
    fun siSeCaeLaConexionEntreEvidenciasSoloReenviaLasPendientes() = runBlocking {
        conEvidencias("E1", "E2")
        gateway.respuestasEvidencia["E2"] = ResultadoApi.SinConexion

        coordinador.registrar(solicitudHu04())

        assertEquals(MensajesSiniestros.EVIDENCIAS_PENDIENTES, coordinador.estado.errorFormulario)
        val parcial = borradores.porUsuario.getValue("USR-1")
        assertEquals("SIN-NUEVO", parcial.siniestroId)
        assertTrue(parcial.registrado)
        assertEquals(listOf("E2"), parcial.pendientes.map { it.id })

        // Vuelve la señal: no se registra otra vez el siniestro y solo se sube E2.
        gateway.respuestasEvidencia.remove("E2")
        coordinador.registrar(solicitudHu04())

        assertEquals(1, gateway.solicitudes.size)
        assertEquals(listOf("E1", "E2", "E2"), gateway.evidenciasSubidas.map { it.second })
        assertTrue(coordinador.estado.registroExitoso)
        assertNull(borradores.porUsuario["USR-1"])
    }

    @Test
    fun elBorradorRegistradoSeRetomaDespuesDeReabrirLaApp() = runBlocking {
        borradores.porUsuario["USR-1"] = BorradorSiniestro(
            id = "BORRADOR-VIEJO",
            polizaId = "POL-1",
            descripcion = "Se rompió la pantalla del celular.",
            evidencias = listOf(evidencia(id = "E1", subida = true), evidencia(id = "E2")),
            siniestroId = "SIN-77"
        )

        coordinador.cargarBorrador()
        assertEquals("BORRADOR-VIEJO", coordinador.estado.borrador?.id)

        coordinador.registrar(solicitudHu04())

        assertTrue(gateway.solicitudes.isEmpty())
        assertEquals(listOf("SIN-77" to "E2"), gateway.evidenciasSubidas)
        assertTrue(coordinador.estado.registroExitoso)
    }

    @Test
    fun evidenciaRechazadaPorElBackendConservaElBorrador() = runBlocking {
        conEvidencias("E1")
        gateway.respuestasEvidencia["E1"] =
            ResultadoApi.Fallo(415, "TIPO_NO_PERMITIDO", "Solo se aceptan fotos JPEG o PNG.")

        coordinador.registrar(solicitudHu04())

        assertEquals(MensajesSiniestros.FORMATO_NO_PERMITIDO, coordinador.estado.errorFormulario)
        assertNotNull(borradores.porUsuario["USR-1"])
        assertFalse(coordinador.estado.registroExitoso)
    }

    @Test
    fun huellaDistintaPideVolverACapturar() = runBlocking {
        conEvidencias("E1")
        gateway.respuestasEvidencia["E1"] = ResultadoApi.Fallo(422, "HUELLA_NO_COINCIDE", null)

        coordinador.registrar(solicitudHu04())

        assertEquals(MensajesSiniestros.EVIDENCIA_ALTERADA, coordinador.estado.errorFormulario)
    }

    @Test
    fun archivoBorradoDelDispositivoSeInforma() = runBlocking {
        conEvidencias("E1")
        gateway.respuestasEvidencia["E1"] =
            ResultadoApi.Fallo(0, CODIGO_ARCHIVO_LOCAL_AUSENTE, null)

        coordinador.registrar(solicitudHu04())

        assertEquals(MensajesSiniestros.ARCHIVO_LOCAL_AUSENTE, coordinador.estado.errorFormulario)
    }

    @Test
    fun errorDelServidorAlSubirDejaLasEvidenciasPendientes() = runBlocking {
        conEvidencias("E1")
        gateway.respuestasEvidencia["E1"] = ResultadoApi.Fallo(503, "ALMACEN_NO_DISPONIBLE", null)

        coordinador.registrar(solicitudHu04())

        assertEquals(MensajesSiniestros.EVIDENCIAS_PENDIENTES, coordinador.estado.errorFormulario)
    }

    @Test
    fun polizaNoVigenteNoSubeEvidencias() = runBlocking {
        conEvidencias("E1")
        gateway.respuestaRegistro = ResultadoApi.Fallo(409, "POLIZA_NO_VIGENTE", null)

        coordinador.registrar(solicitudHu04())

        assertEquals(MensajesSiniestros.POLIZA_NO_VIGENTE, coordinador.estado.errorFormulario)
        assertTrue(gateway.evidenciasSubidas.isEmpty())
        assertNotNull(borradores.porUsuario["USR-1"])
    }

    @Test
    fun token401AlSubirCierraLaSesionYConservaElBorrador() = runBlocking {
        conEvidencias("E1")
        gateway.respuestasEvidencia["E1"] = ResultadoApi.Fallo(401, "TOKEN_EXPIRED", null)

        coordinador.registrar(solicitudHu04())

        assertEquals(1, sesion.rechazos)
        assertEquals(MensajesSiniestros.SESION_VENCIDA, coordinador.estado.mensaje)
        assertNotNull(borradores.porUsuario["USR-1"])
    }

    @Test
    fun sinUsuarioIdentificadoUsaElRegistroSinBorrador() = runBlocking {
        usuario = null

        coordinador.registrar(solicitud())

        assertTrue(coordinador.estado.registroExitoso)
        assertNull(gateway.solicitudes.single().claveIdempotencia)
        assertTrue(borradores.porUsuario.isEmpty())
    }

    // --- Adjuntar y quitar evidencias ------------------------------------------------------

    @Test
    fun evidenciaConUbicacionNoGeneraAviso() = runBlocking {
        coordinador.agregarEvidencia(EvidenciaImportada.Lista(evidencia(id = "E1")))

        assertNull(coordinador.estado.avisoEvidencia)
        assertEquals(listOf("E1"), coordinador.estado.borrador?.evidencias?.map { it.id })
        assertEquals(1, borradores.guardados)
    }

    @Test
    fun evidenciaSinUbicacionInformaQueSeEnviaraSinGeoetiqueta() = runBlocking {
        coordinador.agregarEvidencia(EvidenciaImportada.Lista(evidencia(id = "E1", ubicacion = null)))

        assertEquals(MensajesSiniestros.SIN_UBICACION, coordinador.estado.avisoEvidencia)
        assertFalse(coordinador.estado.borrador!!.evidencias.single().geoetiquetada)
    }

    @Test
    fun archivoDeGaleriaInformaQueVaSinUbicacion() = runBlocking {
        coordinador.agregarEvidencia(
            EvidenciaImportada.Lista(evidencia(id = "E1", ubicacion = null)),
            desdeGaleria = true
        )

        assertEquals(MensajesSiniestros.GALERIA_SIN_UBICACION, coordinador.estado.avisoEvidencia)
    }

    @Test
    fun formatoNoPermitidoSeDescartaYBorraSuArchivo() = runBlocking {
        coordinador.agregarEvidencia(
            EvidenciaImportada.Lista(evidencia(id = "E1", tipoContenido = "image/gif"))
        )

        assertEquals(MensajesSiniestros.FORMATO_NO_PERMITIDO, coordinador.estado.avisoEvidencia)
        assertEquals(listOf("E1"), borradores.archivosEliminados)
        assertNull(coordinador.estado.borrador)
    }

    @Test
    fun capturaRechazadaSoloMuestraElMensaje() = runBlocking {
        coordinador.agregarEvidencia(EvidenciaImportada.Rechazada(MensajesSiniestros.ARCHIVO_VACIO))

        assertEquals(MensajesSiniestros.ARCHIVO_VACIO, coordinador.estado.avisoEvidencia)
        assertNull(coordinador.estado.borrador)
    }

    @Test
    fun noSeAdjuntanMasDeDiezEvidencias() = runBlocking {
        conEvidencias(*Array(ReglasEvidencia.MAXIMO_POR_SINIESTRO) { "E$it" })

        coordinador.agregarEvidencia(EvidenciaImportada.Lista(evidencia(id = "EXTRA")))

        assertEquals(MensajesSiniestros.LIMITE_EVIDENCIAS, coordinador.estado.avisoEvidencia)
        assertEquals(ReglasEvidencia.MAXIMO_POR_SINIESTRO, coordinador.estado.borrador?.evidencias?.size)
        assertTrue("EXTRA" in borradores.archivosEliminados)
    }

    @Test
    fun quitarEvidenciaBorraSuArchivoPeroNoLasYaEnviadas() = runBlocking {
        borradores.porUsuario["USR-1"] = BorradorSiniestro(
            id = "B",
            evidencias = listOf(evidencia(id = "E1", subida = true), evidencia(id = "E2"))
        )
        coordinador.cargarBorrador()

        coordinador.quitarEvidencia("E1")
        coordinador.quitarEvidencia("E2")

        assertEquals(listOf("E1"), coordinador.estado.borrador?.evidencias?.map { it.id })
        assertEquals(listOf("E2"), borradores.archivosEliminados)
    }

    @Test
    fun descartarBorradorEliminaTodo() = runBlocking {
        conEvidencias("E1", "E2")

        coordinador.descartarBorrador()

        assertNull(coordinador.estado.borrador)
        assertTrue(borradores.porUsuario.isEmpty())
        assertEquals(listOf("E1", "E2"), borradores.archivosEliminados)
    }

    @Test
    fun cadaUsuarioVeSoloSuBorrador() = runBlocking {
        borradores.porUsuario["OTRO"] = BorradorSiniestro(id = "AJENO")

        coordinador.cargarBorrador()

        assertNull(coordinador.estado.borrador)
    }

    // --- Reglas -----------------------------------------------------------------------------

    @Test
    fun reglasDeFormatoYTamano() {
        assertEquals(TipoEvidencia.FOTO, ReglasEvidencia.tipoDe("image/png"))
        assertEquals(TipoEvidencia.VIDEO, ReglasEvidencia.tipoDe("VIDEO/MP4; codecs=avc1"))
        assertNull(ReglasEvidencia.tipoDe("image/heic"))
        assertNull(ReglasEvidencia.tipoDe(null))

        assertNull(ReglasEvidencia.error(evidencia(), 0))
        assertEquals(
            MensajesSiniestros.ARCHIVO_DEMASIADO_GRANDE,
            ReglasEvidencia.error(evidencia(tamano = ReglasEvidencia.LIMITE_FOTO_BYTES + 1), 0)
        )
        // Un video puede pesar más que el límite de las fotos.
        assertNull(
            ReglasEvidencia.error(
                evidencia(tipoContenido = "video/mp4", tamano = ReglasEvidencia.LIMITE_FOTO_BYTES + 1),
                0
            )
        )
        assertEquals(MensajesSiniestros.ARCHIVO_VACIO, ReglasEvidencia.error(evidencia(tamano = 0), 0))
    }

    @Test
    fun elBorradorRegistradoNoCambiaSusDatos() {
        val registrado = BorradorSiniestro(id = "B", polizaId = "POL-1", siniestroId = "SIN-1")

        val actualizado = registrado.conDatos(solicitud(polizaId = "POL-2"), 5L)

        assertEquals("POL-1", actualizado.polizaId)
        assertEquals(5L, actualizado.actualizadoEnMs)
    }
}
