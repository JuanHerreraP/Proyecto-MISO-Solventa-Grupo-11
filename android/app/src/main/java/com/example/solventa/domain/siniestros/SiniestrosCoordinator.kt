package com.example.solventa.domain.siniestros

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.SesionAutenticada
import java.util.UUID

/** Estado que observa la UI de siniestros. */
data class EstadoSiniestros(
    val cargando: Boolean = false,
    val siniestros: Siniestros? = null,
    val error: String? = null,
    /** Aviso pasajero, por ejemplo cuando la sesión expira. */
    val mensaje: String? = null,
    /** Registro manual en curso. */
    val registrando: Boolean = false,
    /** Error del formulario de registro (se muestra en la pantalla de registro). */
    val errorFormulario: String? = null,
    /** Evento: el registro manual terminó bien; la UI debe volver a la lista y consumirlo. */
    val registroExitoso: Boolean = false,
    /** Reporte con evidencias sin terminar de enviar (HU04); null si no hay. */
    val borrador: BorradorSiniestro? = null,
    /** Aviso sobre la última evidencia: sin ubicación, formato no permitido, etc. */
    val avisoEvidencia: String? = null
)

object MensajesSiniestros {
    const val SIN_CONEXION =
        "No pudimos conectarnos con Solventa. Revisa tu conexión e inténtalo de nuevo."
    const val ERROR_GENERICO =
        "No pudimos cargar tus siniestros. Inténtalo de nuevo en unos minutos."
    const val SESION_VENCIDA = "Tu sesión expiró. Vuelve a ingresar."
    const val REGISTRO_FALLIDO = "No pudimos registrar el siniestro. Inténtalo de nuevo."
    const val POLIZA_NO_ENCONTRADA = "No encontramos esa póliza en tu billetera."
    const val POLIZA_AJENA = "No tienes acceso a esta póliza."
    const val POLIZA_NO_VIGENTE = "La póliza no está vigente."
    const val DATOS_INVALIDOS = "Revisa los datos del siniestro e inténtalo de nuevo."
    const val CLIENTE_NO_ASOCIADO = "El cliente no está asociado a tu cuenta de asesor."

    // HU04: evidencias y borrador.
    const val BORRADOR_GUARDADO =
        "No hay conexión. Guardamos tu reporte como borrador: envíalo cuando vuelvas a tener señal."
    const val EVIDENCIAS_PENDIENTES =
        "Tu siniestro quedó registrado, pero faltan evidencias por enviar. Las guardamos para " +
            "enviarlas cuando vuelvas a tener conexión."
    const val SIN_UBICACION =
        "No autorizaste la ubicación: la evidencia se enviará sin geoetiqueta."
    const val GALERIA_SIN_UBICACION =
        "Los archivos de la galería se envían sin ubicación."
    const val FORMATO_NO_PERMITIDO = "Solo puedes adjuntar fotos JPG o PNG y videos MP4 o 3GP."
    const val ARCHIVO_VACIO = "El archivo está vacío."
    const val ARCHIVO_DEMASIADO_GRANDE = "La foto puede pesar hasta 10 MB y el video hasta 50 MB."
    const val LIMITE_EVIDENCIAS = "Puedes adjuntar hasta 10 evidencias por siniestro."
    const val EVIDENCIA_RECHAZADA =
        "Una de las evidencias no se pudo enviar. Quítala e inténtalo de nuevo."
    const val EVIDENCIA_ALTERADA =
        "Una evidencia llegó incompleta. Quítala, vuelve a capturarla e inténtalo de nuevo."
    const val SINIESTRO_CERRADO =
        "El siniestro ya fue evaluado y no admite nuevas evidencias."
    const val ARCHIVO_LOCAL_AUSENTE =
        "No encontramos el archivo de una evidencia en el dispositivo. Quítala e inténtalo de nuevo."
}

/**
 * Reglas de los siniestros del cliente (HU20, HU04), sin dependencias de Android.
 *
 * - Pide al backend solo los siniestros del usuario autenticado; el filtro lo hace el backend
 *   con la identidad del token, la app nunca envía un identificador de cliente.
 * - Si el backend rechaza el token (401), la sesión se cierra.
 * - Al cerrar sesión se descarta todo lo cargado. Una respuesta que llega después de limpiar se
 *   ignora: pertenece a la sesión anterior.
 * - Con [borradores] (HU04), el reporte del cliente y sus evidencias se guardan en el dispositivo
 *   antes de enviarse. Si se pierde la conexión quedan como borrador y el siguiente intento
 *   continúa donde iba: el siniestro no se duplica (Idempotency-Key = id del borrador) y solo se
 *   suben las evidencias que faltan. El borrador se elimina cuando todo llegó al backend.
 */
class SiniestrosCoordinator(
    private val gateway: SiniestrosGateway,
    private val sesion: SesionAutenticada,
    private val borradores: BorradoresSiniestro? = null,
    private val usuarioActual: () -> String? = { null },
    private val reloj: () -> Long = { System.currentTimeMillis() },
    private val generarId: () -> String = { UUID.randomUUID().toString() }
) {
    var observador: ((EstadoSiniestros) -> Unit)? = null
        set(value) {
            field = value
            value?.invoke(estado)
        }

    var estado: EstadoSiniestros = EstadoSiniestros()
        private set(value) {
            field = value
            observador?.invoke(value)
        }

    /** Cambia al limpiar; una respuesta de otra generación ya no se aplica. */
    private var generacion = 0

    suspend fun cargar() {
        if (estado.cargando) return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(cargando = true, error = null)
        val inicio = generacion
        val resultado = gateway.listar(token)
        if (inicio != generacion) return

        estado = when (resultado) {
            is ResultadoApi.Exito -> estado.copy(cargando = false, siniestros = resultado.valor)
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) return rechazada()
                estado.copy(cargando = false, error = MensajesSiniestros.ERROR_GENERICO)
            }
            ResultadoApi.SinConexion ->
                estado.copy(cargando = false, error = MensajesSiniestros.SIN_CONEXION)
        }
    }

    fun consumirMensaje() {
        if (estado.mensaje != null) estado = estado.copy(mensaje = null)
    }

    /**
     * Registra manualmente un siniestro (HU20). Si el backend lo acepta, recarga la lista para
     * que el nuevo siniestro aparezca y marca [registroExitoso] para que la UI vuelva a la lista.
     *
     * Con borradores disponibles (HU04) el registro pasa por el borrador y envía las evidencias.
     */
    suspend fun registrar(solicitud: SolicitudSiniestro) {
        val usuarioId = usuarioActual()
        if (borradores != null && usuarioId != null) {
            return registrarConEvidencias(solicitud, borradores, usuarioId)
        }
        if (estado.registrando) return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(registrando = true, errorFormulario = null, registroExitoso = false)
        val inicio = generacion
        val resultado = gateway.registrar(token, solicitud)
        if (inicio != generacion) return

        when (resultado) {
            is ResultadoApi.Exito -> {
                estado = estado.copy(registrando = false, errorFormulario = null, registroExitoso = true)
                // El backend es la fuente de verdad: se recarga la lista con el nuevo siniestro.
                cargar()
            }
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) return rechazada()
                estado = estado.copy(
                    registrando = false,
                    errorFormulario = mensajeRegistro(resultado.http)
                )
            }
            ResultadoApi.SinConexion ->
                estado = estado.copy(registrando = false, errorFormulario = MensajesSiniestros.SIN_CONEXION)
        }
    }

    fun consumirRegistroExitoso() {
        if (estado.registroExitoso) estado = estado.copy(registroExitoso = false)
    }

    fun consumirErrorFormulario() {
        if (estado.errorFormulario != null) estado = estado.copy(errorFormulario = null)
    }

    /**
     * Registra un siniestro asistido por un asesor (HU20), en nombre del cliente indicado.
     * El backend valida la asociación asesor-cliente y la titularidad de la póliza.
     */
    suspend fun registrarAsistido(solicitud: SolicitudSiniestroAsistido) {
        if (estado.registrando) return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(registrando = true, errorFormulario = null, registroExitoso = false)
        val inicio = generacion
        val resultado = gateway.registrarAsistido(token, solicitud)
        if (inicio != generacion) return

        when (resultado) {
            is ResultadoApi.Exito ->
                estado = estado.copy(registrando = false, errorFormulario = null, registroExitoso = true)
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) return rechazada()
                val mensaje = if (resultado.http == 403 && resultado.codigo == "CLIENTE_NO_ASOCIADO") {
                    MensajesSiniestros.CLIENTE_NO_ASOCIADO
                } else {
                    mensajeRegistro(resultado.http)
                }
                estado = estado.copy(registrando = false, errorFormulario = mensaje)
            }
            ResultadoApi.SinConexion ->
                estado = estado.copy(registrando = false, errorFormulario = MensajesSiniestros.SIN_CONEXION)
        }
    }

    /** Carga el borrador del usuario, si dejó un reporte sin terminar de enviar (HU04). */
    suspend fun cargarBorrador() {
        val almacen = borradores ?: return
        val usuarioId = usuarioActual() ?: return
        val inicio = generacion
        val borrador = almacen.leer(usuarioId)
        if (inicio != generacion) return
        estado = estado.copy(borrador = borrador)
    }

    /**
     * Adjunta una evidencia capturada o importada al borrador (HU04). Si no cumple las reglas,
     * se descarta su archivo y se informa por qué. Se avisa cuando va sin ubicación.
     */
    suspend fun agregarEvidencia(importada: EvidenciaImportada, desdeGaleria: Boolean = false) {
        val almacen = borradores ?: return
        val usuarioId = usuarioActual() ?: return
        val evidencia = when (importada) {
            is EvidenciaImportada.Rechazada -> {
                estado = estado.copy(avisoEvidencia = importada.mensaje)
                return
            }
            is EvidenciaImportada.Lista -> importada.evidencia
        }
        val actual = estado.borrador ?: BorradorSiniestro(id = generarId())
        val error = ReglasEvidencia.error(evidencia, actual.evidencias.size)
        if (error != null) {
            almacen.eliminarArchivo(evidencia)
            estado = estado.copy(avisoEvidencia = error)
            return
        }
        val borrador = actual.copy(
            evidencias = actual.evidencias + evidencia,
            actualizadoEnMs = reloj()
        )
        almacen.guardar(usuarioId, borrador)
        val aviso = when {
            evidencia.geoetiquetada -> null
            desdeGaleria -> MensajesSiniestros.GALERIA_SIN_UBICACION
            else -> MensajesSiniestros.SIN_UBICACION
        }
        estado = estado.copy(borrador = borrador, avisoEvidencia = aviso)
    }

    /** Quita una evidencia que aún no se envió y borra su archivo. */
    suspend fun quitarEvidencia(evidenciaId: String) {
        val almacen = borradores ?: return
        val usuarioId = usuarioActual() ?: return
        val actual = estado.borrador ?: return
        val evidencia = actual.evidencias.firstOrNull { it.id == evidenciaId && !it.subida } ?: return
        val borrador = actual.copy(
            evidencias = actual.evidencias.filterNot { it.id == evidenciaId },
            actualizadoEnMs = reloj()
        )
        almacen.eliminarArchivo(evidencia)
        almacen.guardar(usuarioId, borrador)
        estado = estado.copy(borrador = borrador, avisoEvidencia = null)
    }

    /** Descarta el borrador y sus archivos. Lo que ya se envió queda en el backend. */
    suspend fun descartarBorrador() {
        val almacen = borradores ?: return
        val usuarioId = usuarioActual() ?: return
        almacen.eliminar(usuarioId)
        estado = estado.copy(borrador = null, avisoEvidencia = null, errorFormulario = null)
    }

    fun consumirAvisoEvidencia() {
        if (estado.avisoEvidencia != null) estado = estado.copy(avisoEvidencia = null)
    }

    /**
     * Envía el reporte del cliente con sus evidencias (HU04).
     *
     * 1. Guarda el borrador con los datos del formulario antes de usar la red.
     * 2. Si el siniestro aún no existe, lo registra con el id del borrador como Idempotency-Key.
     * 3. Sube, una por una, las evidencias que faltan; cada una se marca al llegar.
     * 4. Con todo enviado, elimina el borrador y recarga la lista.
     *
     * Sin conexión en cualquier paso, el borrador queda guardado con el avance.
     */
    private suspend fun registrarConEvidencias(
        solicitud: SolicitudSiniestro,
        almacen: BorradoresSiniestro,
        usuarioId: String
    ) {
        if (estado.registrando) return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(
            registrando = true,
            errorFormulario = null,
            registroExitoso = false,
            avisoEvidencia = null
        )
        val inicio = generacion
        var borrador = (estado.borrador ?: BorradorSiniestro(id = generarId()))
            .conDatos(solicitud, reloj())
        almacen.guardar(usuarioId, borrador)
        if (inicio != generacion) return
        estado = estado.copy(borrador = borrador)

        val siniestroId = borrador.siniestroId ?: run {
            val resultado = gateway.registrar(
                token,
                solicitud.copy(claveIdempotencia = borrador.id)
            )
            if (inicio != generacion) return
            when (resultado) {
                is ResultadoApi.Exito -> resultado.valor.siniestroId
                is ResultadoApi.Fallo -> {
                    if (resultado.http == 401) return rechazada()
                    estado = estado.copy(
                        registrando = false,
                        errorFormulario = mensajeRegistro(resultado.http)
                    )
                    return
                }
                ResultadoApi.SinConexion -> {
                    estado = estado.copy(
                        registrando = false,
                        errorFormulario = MensajesSiniestros.BORRADOR_GUARDADO
                    )
                    return
                }
            }
        }
        if (borrador.siniestroId == null) {
            borrador = borrador.copy(siniestroId = siniestroId, actualizadoEnMs = reloj())
            almacen.guardar(usuarioId, borrador)
            if (inicio != generacion) return
            estado = estado.copy(borrador = borrador)
        }

        for (evidencia in borrador.pendientes) {
            val resultado = gateway.subirEvidencia(token, siniestroId, evidencia)
            if (inicio != generacion) return
            when (resultado) {
                is ResultadoApi.Exito -> {
                    borrador = borrador.marcarSubida(evidencia.id)
                    almacen.guardar(usuarioId, borrador)
                    if (inicio != generacion) return
                    estado = estado.copy(borrador = borrador)
                }
                is ResultadoApi.Fallo -> {
                    if (resultado.http == 401) return rechazada()
                    estado = estado.copy(
                        registrando = false,
                        errorFormulario = mensajeEvidencia(resultado)
                    )
                    return
                }
                ResultadoApi.SinConexion -> {
                    estado = estado.copy(
                        registrando = false,
                        errorFormulario = MensajesSiniestros.EVIDENCIAS_PENDIENTES
                    )
                    return
                }
            }
        }

        almacen.eliminar(usuarioId)
        if (inicio != generacion) return
        estado = estado.copy(
            registrando = false,
            errorFormulario = null,
            registroExitoso = true,
            borrador = null
        )
        cargar()
    }

    /** Se llama al cerrar o perder la sesión. */
    fun limpiar() {
        generacion++
        if (estado != EstadoSiniestros()) estado = EstadoSiniestros()
    }

    private fun tokenOFinalizar(): String? {
        val token = sesion.accessTokenVigente()
        if (token == null) rechazada()
        return token
    }

    private fun rechazada() {
        generacion++
        estado = EstadoSiniestros(mensaje = MensajesSiniestros.SESION_VENCIDA)
        sesion.sesionRechazada()
    }

    private fun mensajeEvidencia(fallo: ResultadoApi.Fallo): String = when (fallo.codigo) {
        "TIPO_NO_PERMITIDO", "CONTENIDO_NO_COINCIDE" -> MensajesSiniestros.FORMATO_NO_PERMITIDO
        "ARCHIVO_VACIO" -> MensajesSiniestros.ARCHIVO_VACIO
        "ARCHIVO_DEMASIADO_GRANDE" -> MensajesSiniestros.ARCHIVO_DEMASIADO_GRANDE
        "LIMITE_EVIDENCIAS" -> MensajesSiniestros.LIMITE_EVIDENCIAS
        "HUELLA_NO_COINCIDE" -> MensajesSiniestros.EVIDENCIA_ALTERADA
        "SINIESTRO_CERRADO" -> MensajesSiniestros.SINIESTRO_CERRADO
        CODIGO_ARCHIVO_LOCAL_AUSENTE -> MensajesSiniestros.ARCHIVO_LOCAL_AUSENTE
        else -> if (fallo.http >= 500) {
            MensajesSiniestros.EVIDENCIAS_PENDIENTES
        } else {
            MensajesSiniestros.EVIDENCIA_RECHAZADA
        }
    }

    private fun mensajeRegistro(http: Int): String = when (http) {
        404 -> MensajesSiniestros.POLIZA_NO_ENCONTRADA
        403 -> MensajesSiniestros.POLIZA_AJENA
        409 -> MensajesSiniestros.POLIZA_NO_VIGENTE
        422 -> MensajesSiniestros.DATOS_INVALIDOS
        else -> MensajesSiniestros.REGISTRO_FALLIDO
    }
}

/** Código que usa el gateway cuando el archivo de una evidencia ya no está en el dispositivo. */
const val CODIGO_ARCHIVO_LOCAL_AUSENTE = "ARCHIVO_LOCAL_AUSENTE"
