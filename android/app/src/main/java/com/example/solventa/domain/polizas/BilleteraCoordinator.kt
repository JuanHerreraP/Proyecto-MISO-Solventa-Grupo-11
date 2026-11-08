package com.example.solventa.domain.polizas

import com.example.solventa.domain.auth.Reloj
import com.example.solventa.domain.auth.ResultadoApi

/** Estado que observa la UI de la billetera y del certificado. */
data class EstadoBilletera(
    val cargando: Boolean = false,
    val billetera: Billetera? = null,
    val error: String? = null,
    /** True cuando la información visible proviene del almacenamiento local cifrado. */
    val usandoDatosLocales: Boolean = false,
    val sinConexion: Boolean = false,
    val ultimaSincronizacionMs: Long? = null,
    val datosAntiguos: Boolean = false,
    val falloSincronizacionPersistente: Boolean = false,
    val cargandoCertificado: Boolean = false,
    val certificado: Certificado? = null,
    val errorCertificado: String? = null,
    val cargandoHistorial: Boolean = false,
    val historialEndosos: HistorialEndosos? = null,
    val errorHistorial: String? = null,
    val descargandoDocumento: Boolean = false,
    /** Evento: la UI abre este PDF y luego lo consume. */
    val documentoParaAbrir: DocumentoPoliza? = null,
    val compartiendo: Boolean = false,
    /** Evento: la UI debe abrir el menú de compartir con este enlace y luego consumirlo. */
    val enlaceParaCompartir: EnlaceCompartido? = null,
    /** Aviso pasajero, por ejemplo cuando no se pudo generar el enlace. */
    val mensaje: String? = null
)

object MensajesBilletera {
    const val SIN_CONEXION =
        "No pudimos conectarnos con Solventa. Revisa tu conexión e inténtalo de nuevo."
    const val ERROR_GENERICO = "No pudimos cargar tu billetera. Inténtalo de nuevo en unos minutos."
    const val POLIZA_NO_ENCONTRADA = "No encontramos esa póliza en tu billetera."
    const val CERTIFICADO_NO_DISPONIBLE = "No pudimos cargar el certificado. Inténtalo de nuevo."
    const val HISTORIAL_NO_DISPONIBLE = "No pudimos cargar el historial. Inténtalo de nuevo."
    const val DOCUMENTO_NO_DISPONIBLE = "No pudimos abrir el documento. Inténtalo de nuevo."
    const val DOCUMENTO_REQUIERE_CONEXION = "Conéctate a internet para consultar el documento."
    const val COMPARTIR_FALLIDO = "No pudimos generar el enlace para compartir. Inténtalo de nuevo."
    const val SESION_VENCIDA = "Tu sesión expiró. Vuelve a ingresar."
}

enum class ResultadoSincronizacion {
    EXITO,
    REINTENTAR,
    SIN_SESION,
    EN_CURSO
}

/**
 * Reglas de la HU07 (BPM-31), sin dependencias de Android.
 *
 * - Pide al backend solo las pólizas del usuario autenticado; el filtro lo hace el backend
 *   con la identidad del token, la app nunca envía un identificador de cliente.
 * - Si el backend rechaza el token (401), la sesión se cierra.
 * - Al cerrar sesión se descarta todo lo cargado, para que otro usuario no lo vea. Una
 *   respuesta que llega después de limpiar se ignora: pertenece a la sesión anterior.
 */
class BilleteraCoordinator(
    private val gateway: PolizasGateway,
    private val sesion: SesionPolizasOffline,
    private val cache: CachePolizas,
    private val reloj: Reloj
) {
    var observador: ((EstadoBilletera) -> Unit)? = null
        set(value) {
            field = value
            value?.invoke(estado)
        }

    var estado: EstadoBilletera = EstadoBilletera()
        private set(value) {
            field = value
            observador?.invoke(value)
        }

    /** Cambia al limpiar; una respuesta de otra generación ya no se aplica. */
    private var generacion = 0
    private var usuarioActivo: ClaveUsuarioCache? = null

    suspend fun cargar() {
        actualizar(informarFallo = true)
    }

    /** Actualiza sin bloquear la UI ni mostrar errores durante los reintentos automáticos. */
    suspend fun sincronizarEnSegundoPlano(): ResultadoSincronizacion =
        actualizar(informarFallo = false)

    fun marcarFalloSincronizacionPersistente() {
        if (sesion.usuarioId() != null) {
            estado = estado.copy(falloSincronizacionPersistente = true)
        }
    }

    private suspend fun actualizar(informarFallo: Boolean): ResultadoSincronizacion {
        if (estado.cargando) return ResultadoSincronizacion.EN_CURSO
        val usuarioId = sesion.usuarioId()
        val token = sesion.accessTokenVigente()
        if (usuarioId == null || token == null) {
            if (informarFallo) rechazada()
            return ResultadoSincronizacion.SIN_SESION
        }
        val usuario = ClaveUsuarioCache(usuarioId)
        activarUsuario(usuario)
        val cacheada = leerBilletera(usuario)
        estado = estado.copy(
            cargando = true,
            billetera = cacheada?.billetera ?: estado.billetera,
            error = null,
            usandoDatosLocales = cacheada != null,
            sinConexion = false,
            ultimaSincronizacionMs = cacheada?.metadatos?.sincronizadaEnMs,
            datosAntiguos = cacheada?.metadatos?.superaAntiguedadMaxima(reloj.ahoraMs()) == true,
            falloSincronizacionPersistente = false
        )
        val inicio = generacion
        val resultado = gateway.billetera(token)
        if (inicio != generacion) return ResultadoSincronizacion.SIN_SESION

        when (resultado) {
            is ResultadoApi.Exito -> {
                val sincronizadaEnMs = reloj.ahoraMs()
                guardarBilletera(usuario, resultado.valor, sincronizadaEnMs)
                estado = estado.copy(
                    cargando = false,
                    billetera = resultado.valor,
                    error = null,
                    usandoDatosLocales = false,
                    sinConexion = false,
                    ultimaSincronizacionMs = sincronizadaEnMs,
                    datosAntiguos = false,
                    falloSincronizacionPersistente = false
                )
                return ResultadoSincronizacion.EXITO
            }
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) {
                    rechazada()
                    return ResultadoSincronizacion.SIN_SESION
                }
                estado = estado.copy(
                    cargando = false,
                    error = if (informarFallo) MensajesBilletera.ERROR_GENERICO else estado.error
                )
            }
            ResultadoApi.SinConexion -> estado = if (cacheada != null) {
                estado.copy(cargando = false, error = null, sinConexion = true)
            } else {
                estado.copy(
                    cargando = false,
                    error = if (informarFallo) MensajesBilletera.SIN_CONEXION else null,
                    sinConexion = true
                )
            }
        }
        return ResultadoSincronizacion.REINTENTAR
    }

    suspend fun verCertificado(polizaId: String) {
        if (estado.cargandoCertificado) return
        val usuario = usuarioOFinalizar() ?: return
        activarUsuario(usuario)
        val token = tokenOFinalizar() ?: return
        val cacheado = leerCertificado(usuario, polizaId)
        estado = estado.copy(
            cargandoCertificado = true,
            certificado = cacheado?.certificado
                ?: estado.certificado?.takeIf { it.polizaId == polizaId },
            errorCertificado = null
        )
        val inicio = generacion
        val resultado = gateway.certificado(token, polizaId)
        if (inicio != generacion) return

        estado = when (resultado) {
            is ResultadoApi.Exito -> {
                guardarCertificado(usuario, resultado.valor)
                estado.copy(cargandoCertificado = false, certificado = resultado.valor)
            }
            is ResultadoApi.Fallo -> when (resultado.http) {
                401 -> return rechazada()
                403, 404 -> estado.copy(
                    cargandoCertificado = false,
                    certificado = null,
                    errorCertificado = MensajesBilletera.POLIZA_NO_ENCONTRADA
                )
                else -> estado.copy(
                    cargandoCertificado = false,
                    errorCertificado = MensajesBilletera.CERTIFICADO_NO_DISPONIBLE
                )
            }
            ResultadoApi.SinConexion -> if (cacheado != null) {
                estado.copy(cargandoCertificado = false, certificado = cacheado.certificado)
            } else {
                estado.copy(
                    cargandoCertificado = false,
                    errorCertificado = MensajesBilletera.SIN_CONEXION
                )
            }
        }
    }

    suspend fun compartir(polizaId: String) {
        if (estado.compartiendo) return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(compartiendo = true, mensaje = null)
        val inicio = generacion
        val resultado = gateway.compartir(token, polizaId)
        if (inicio != generacion) return

        estado = when (resultado) {
            is ResultadoApi.Exito -> estado.copy(compartiendo = false, enlaceParaCompartir = resultado.valor)
            is ResultadoApi.Fallo -> when (resultado.http) {
                401 -> return rechazada()
                403, 404 -> estado.copy(compartiendo = false, mensaje = MensajesBilletera.POLIZA_NO_ENCONTRADA)
                else -> estado.copy(compartiendo = false, mensaje = MensajesBilletera.COMPARTIR_FALLIDO)
            }
            ResultadoApi.SinConexion -> estado.copy(compartiendo = false, mensaje = MensajesBilletera.SIN_CONEXION)
        }
    }

    /** Consulta el historial remoto y conserva la última copia cifrada para uso offline. */
    suspend fun verHistorialEndosos(polizaId: String) {
        if (estado.cargandoHistorial) return
        val usuario = usuarioOFinalizar() ?: return
        activarUsuario(usuario)
        val token = tokenOFinalizar() ?: return
        val cacheado = leerHistorialEndosos(usuario, polizaId)
        estado = estado.copy(
            cargandoHistorial = true,
            historialEndosos = cacheado?.historial,
            errorHistorial = null
        )
        val inicio = generacion
        val resultado = gateway.historialEndosos(token, polizaId)
        if (inicio != generacion) return

        estado = when (resultado) {
            is ResultadoApi.Exito -> {
                guardarHistorialEndosos(usuario, polizaId, resultado.valor)
                estado.copy(cargandoHistorial = false, historialEndosos = resultado.valor)
            }
            is ResultadoApi.Fallo -> when (resultado.http) {
                401 -> return rechazada()
                403, 404 -> estado.copy(
                    cargandoHistorial = false,
                    historialEndosos = null,
                    errorHistorial = MensajesBilletera.POLIZA_NO_ENCONTRADA
                )
                else -> estado.copy(
                    cargandoHistorial = false,
                    errorHistorial = MensajesBilletera.HISTORIAL_NO_DISPONIBLE
                )
            }
            ResultadoApi.SinConexion -> if (cacheado != null) {
                estado.copy(cargandoHistorial = false, historialEndosos = cacheado.historial)
            } else {
                estado.copy(
                    cargandoHistorial = false,
                    errorHistorial = MensajesBilletera.SIN_CONEXION
                )
            }
        }
    }

    suspend fun descargarDocumento(polizaId: String) {
        if (estado.descargandoDocumento) return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(descargandoDocumento = true, mensaje = null)
        val inicio = generacion
        val resultado = gateway.documento(token, polizaId)
        if (inicio != generacion) return

        estado = when (resultado) {
            is ResultadoApi.Exito -> estado.copy(
                descargandoDocumento = false,
                documentoParaAbrir = resultado.valor
            )
            is ResultadoApi.Fallo -> when (resultado.http) {
                401 -> return rechazada()
                403, 404 -> estado.copy(
                    descargandoDocumento = false,
                    mensaje = MensajesBilletera.POLIZA_NO_ENCONTRADA
                )
                else -> estado.copy(
                    descargandoDocumento = false,
                    mensaje = MensajesBilletera.DOCUMENTO_NO_DISPONIBLE
                )
            }
            ResultadoApi.SinConexion -> estado.copy(
                descargandoDocumento = false,
                mensaje = MensajesBilletera.DOCUMENTO_REQUIERE_CONEXION
            )
        }
    }

    fun documentoAbierto(exito: Boolean) {
        if (estado.documentoParaAbrir == null) return
        estado = estado.copy(
            documentoParaAbrir = null,
            mensaje = if (exito) estado.mensaje else MensajesBilletera.DOCUMENTO_NO_DISPONIBLE
        )
    }

    fun enlaceCompartido() {
        if (estado.enlaceParaCompartir != null) estado = estado.copy(enlaceParaCompartir = null)
    }

    fun consumirMensaje() {
        if (estado.mensaje != null) estado = estado.copy(mensaje = null)
    }

    fun cerrarCertificado() {
        estado = estado.copy(
            cargandoCertificado = false,
            certificado = null,
            errorCertificado = null,
            cargandoHistorial = false,
            historialEndosos = null,
            errorHistorial = null,
            descargandoDocumento = false,
            documentoParaAbrir = null,
            compartiendo = false,
            enlaceParaCompartir = null,
            mensaje = null
        )
    }

    /** Limpia únicamente la memoria; no borra una caché útil al iniciar la app sin conexión. */
    fun limpiar() {
        generacion++
        if (estado != EstadoBilletera()) estado = EstadoBilletera()
    }

    /** Se llama después de una transición real de sesión autenticada a sesión cerrada. */
    suspend fun eliminarDatosLocales() {
        limpiar()
        usuarioActivo = null
        try {
            cache.eliminarTodo()
        } catch (error: Exception) {
            // El estado en memoria ya quedó limpio; el almacenamiento reintentará al próximo acceso.
        }
    }

    /** Registra la identidad actual y elimina cualquier dato perteneciente a otra sesión. */
    suspend fun registrarUsuario(usuarioId: String) {
        activarUsuario(ClaveUsuarioCache(usuarioId))
    }

    private fun tokenOFinalizar(): String? {
        val token = sesion.accessTokenVigente()
        if (token == null) rechazada()
        return token
    }

    private fun usuarioOFinalizar(): ClaveUsuarioCache? {
        val usuarioId = sesion.usuarioId()
        if (usuarioId == null) {
            rechazada()
            return null
        }
        return ClaveUsuarioCache(usuarioId)
    }

    private suspend fun leerBilletera(usuario: ClaveUsuarioCache): BilleteraCacheada? =
        try {
            cache.billetera(usuario)
        } catch (error: Exception) {
            null
        }

    private suspend fun leerCertificado(
        usuario: ClaveUsuarioCache,
        polizaId: String
    ): CertificadoCacheado? = try {
        cache.certificado(usuario, polizaId)
    } catch (error: Exception) {
        null
    }

    private suspend fun leerHistorialEndosos(
        usuario: ClaveUsuarioCache,
        polizaId: String
    ): HistorialEndososCacheado? = try {
        cache.historialEndosos(usuario, polizaId)
    } catch (error: Exception) {
        null
    }

    private suspend fun guardarBilletera(
        usuario: ClaveUsuarioCache,
        billetera: Billetera,
        sincronizadaEnMs: Long
    ) {
        try {
            val certificados = billetera.polizas.mapNotNull { poliza ->
                cache.certificado(usuario, poliza.polizaId)?.certificado
            }
            cache.reemplazar(usuario, billetera, certificados, sincronizadaEnMs)
        } catch (error: Exception) {
            // La API sigue siendo utilizable aunque el dispositivo no pueda persistir la caché.
        }
    }

    private suspend fun guardarCertificado(
        usuario: ClaveUsuarioCache,
        certificado: Certificado
    ) {
        try {
            val billeteraCacheada = cache.billetera(usuario) ?: return
            val certificados = billeteraCacheada.billetera.polizas.mapNotNull { poliza ->
                if (poliza.polizaId == certificado.polizaId) certificado
                else cache.certificado(usuario, poliza.polizaId)?.certificado
            }
            cache.reemplazar(
                usuario = usuario,
                billetera = billeteraCacheada.billetera,
                certificados = certificados,
                sincronizadaEnMs = billeteraCacheada.metadatos.sincronizadaEnMs
            )
        } catch (error: Exception) {
            // Mostrar el certificado remoto no depende de que el dispositivo pueda persistirlo.
        }
    }

    private suspend fun guardarHistorialEndosos(
        usuario: ClaveUsuarioCache,
        polizaId: String,
        historial: HistorialEndosos
    ) {
        try {
            cache.guardarHistorialEndosos(usuario, polizaId, historial)
        } catch (error: Exception) {
            // Mostrar el historial remoto no depende de que el dispositivo pueda persistirlo.
        }
    }

    private suspend fun activarUsuario(usuario: ClaveUsuarioCache) {
        val anterior = usuarioActivo
        if (anterior != null && anterior != usuario) {
            limpiar()
            try {
                cache.eliminar(anterior)
            } catch (error: Exception) {
                try {
                    cache.eliminarTodo()
                } catch (errorTotal: Exception) {
                    // El aislamiento en memoria se mantiene aunque falle el almacenamiento.
                }
            }
        }
        usuarioActivo = usuario
    }

    private fun rechazada() {
        generacion++
        estado = EstadoBilletera(mensaje = MensajesBilletera.SESION_VENCIDA)
        sesion.sesionRechazada()
    }
}
