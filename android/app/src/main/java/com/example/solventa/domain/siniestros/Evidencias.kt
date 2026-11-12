package com.example.solventa.domain.siniestros

/** Una foto o un video adjunto al reporte de siniestro (HU04). */
enum class TipoEvidencia { FOTO, VIDEO }

/** Ubicación del dispositivo al capturar la evidencia. */
data class Ubicacion(
    val latitud: Double,
    val longitud: Double,
    val precisionMetros: Float? = null
)

/**
 * Evidencia guardada en el dispositivo mientras el reporte no se envía.
 *
 * El archivo vive en el almacenamiento privado de la app ([rutaArchivo]). La huella SHA-256 se
 * calcula al capturarla: el backend la compara con lo que recibe y rechaza un archivo alterado
 * en el camino. [capturadaEn] va en ISO 8601 UTC. Sin permiso de ubicación (o para archivos de
 * la galería) la evidencia se envía sin geoetiqueta.
 */
data class EvidenciaLocal(
    val id: String,
    val rutaArchivo: String,
    val tipoContenido: String,
    val tipo: TipoEvidencia,
    val tamanoBytes: Long,
    val huellaSha256: String,
    val capturadaEn: String?,
    val ubicacion: Ubicacion?,
    val nombreArchivo: String? = null,
    /** Ya está en el backend; un reintento no la vuelve a enviar. */
    val subida: Boolean = false
) {
    val geoetiquetada: Boolean get() = ubicacion != null
}

/** Lo que el backend registró de una evidencia. */
data class EvidenciaRegistrada(
    val evidenciaId: String,
    val huellaSha256: String,
    val geoetiquetada: Boolean
)

/** Resultado de capturar o importar un archivo. */
sealed interface EvidenciaImportada {
    data class Lista(val evidencia: EvidenciaLocal) : EvidenciaImportada
    data class Rechazada(val mensaje: String) : EvidenciaImportada
}

/**
 * Reporte de siniestro que aún no termina de enviarse (HU04).
 *
 * Se guarda antes de cada intento de envío. Si se pierde la conexión, el cliente lo retoma más
 * tarde: [id] viaja como `Idempotency-Key` para que el backend no duplique el siniestro, y
 * [siniestroId] indica que ya se registró y solo faltan evidencias por subir.
 */
data class BorradorSiniestro(
    val id: String,
    val polizaId: String = "",
    val tipoSiniestro: TipoSiniestro? = null,
    val fechaEvento: String = "",
    val horaEvento: String = "",
    val lugar: String = "",
    val descripcion: String = "",
    val estimacionDanos: String = "",
    val evidencias: List<EvidenciaLocal> = emptyList(),
    val siniestroId: String? = null,
    val actualizadoEnMs: Long = 0
) {
    val pendientes: List<EvidenciaLocal> get() = evidencias.filterNot { it.subida }
    val registrado: Boolean get() = siniestroId != null

    fun conDatos(solicitud: SolicitudSiniestro, ahoraMs: Long): BorradorSiniestro =
        // Una vez registrado, el siniestro no cambia: solo quedan evidencias por enviar.
        if (registrado) {
            copy(actualizadoEnMs = ahoraMs)
        } else {
            copy(
                polizaId = solicitud.polizaId,
                tipoSiniestro = solicitud.tipoSiniestro,
                fechaEvento = solicitud.fechaEvento,
                horaEvento = solicitud.horaEvento,
                lugar = solicitud.lugar,
                descripcion = solicitud.descripcion,
                estimacionDanos = solicitud.estimacionDanos,
                actualizadoEnMs = ahoraMs
            )
        }

    fun marcarSubida(evidenciaId: String): BorradorSiniestro =
        copy(evidencias = evidencias.map { if (it.id == evidenciaId) it.copy(subida = true) else it })
}

/**
 * Borrador del reporte de siniestro en el dispositivo, uno por usuario.
 * La implementación guarda los archivos en el almacenamiento privado de la app.
 */
interface BorradoresSiniestro {
    suspend fun leer(usuarioId: String): BorradorSiniestro?

    suspend fun guardar(usuarioId: String, borrador: BorradorSiniestro)

    /** Elimina el borrador y todos sus archivos. */
    suspend fun eliminar(usuarioId: String)

    /** Elimina el archivo de una evidencia que se descartó. */
    suspend fun eliminarArchivo(evidencia: EvidenciaLocal)
}

/** Formatos y límites alineados con el backend. */
object ReglasEvidencia {
    const val MAXIMO_POR_SINIESTRO = 10
    const val LIMITE_FOTO_BYTES = 10L * 1024 * 1024
    const val LIMITE_VIDEO_BYTES = 50L * 1024 * 1024

    private val formatos = mapOf(
        "image/jpeg" to TipoEvidencia.FOTO,
        "image/png" to TipoEvidencia.FOTO,
        "video/mp4" to TipoEvidencia.VIDEO,
        "video/3gpp" to TipoEvidencia.VIDEO
    )

    fun tipoDe(tipoContenido: String?): TipoEvidencia? =
        tipoContenido?.substringBefore(';')?.trim()?.lowercase()?.let { formatos[it] }

    fun limiteDe(tipo: TipoEvidencia): Long =
        if (tipo == TipoEvidencia.FOTO) LIMITE_FOTO_BYTES else LIMITE_VIDEO_BYTES

    /** Mensaje para el usuario si la evidencia no se puede adjuntar; null si es válida. */
    fun error(evidencia: EvidenciaLocal, cantidadActual: Int): String? {
        val tipo = tipoDe(evidencia.tipoContenido)
        return when {
            tipo == null -> MensajesSiniestros.FORMATO_NO_PERMITIDO
            evidencia.tamanoBytes <= 0 -> MensajesSiniestros.ARCHIVO_VACIO
            evidencia.tamanoBytes > limiteDe(tipo) -> MensajesSiniestros.ARCHIVO_DEMASIADO_GRANDE
            cantidadActual >= MAXIMO_POR_SINIESTRO -> MensajesSiniestros.LIMITE_EVIDENCIAS
            else -> null
        }
    }
}
