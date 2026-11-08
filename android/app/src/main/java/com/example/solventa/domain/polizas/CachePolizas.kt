package com.example.solventa.domain.polizas

const val ANTIGUEDAD_MAXIMA_CACHE_DIAS = 30L

/** Sesión que además identifica al propietario de la caché offline. */
interface SesionPolizasOffline : SesionAutenticada {
    /** ID estable del usuario dueño de los datos locales. Null si no hay sesión activa. */
    fun usuarioId(): String?
}

/**
 * Identifica al propietario de una caché sin almacenar correo, documento ni tokens.
 * La implementación persistente debe usar esta clave en todas sus consultas.
 */
data class ClaveUsuarioCache(val valor: String) {
    init {
        require(valor.isNotBlank()) { "La clave del usuario no puede estar vacía." }
    }
}

/** Datos de la última sincronización completa y exitosa. */
data class MetadatosSincronizacion(
    val usuario: ClaveUsuarioCache,
    val sincronizadaEnMs: Long
) {
    init {
        require(sincronizadaEnMs >= 0) { "La fecha de sincronización no puede ser negativa." }
    }

    fun superaAntiguedadMaxima(
        ahoraMs: Long,
        maximoDias: Long = ANTIGUEDAD_MAXIMA_CACHE_DIAS
    ): Boolean {
        require(maximoDias >= 0) { "La antigüedad máxima no puede ser negativa." }
        if (ahoraMs <= sincronizadaEnMs) return false
        val maximoMs = maximoDias * MILISEGUNDOS_POR_DIA
        return ahoraMs - sincronizadaEnMs > maximoMs
    }

    private companion object {
        const val MILISEGUNDOS_POR_DIA = 24L * 60L * 60L * 1_000L
    }
}

data class BilleteraCacheada(
    val billetera: Billetera,
    val metadatos: MetadatosSincronizacion
)

data class CertificadoCacheado(
    val certificado: Certificado,
    val metadatos: MetadatosSincronizacion
)

data class HistorialEndososCacheado(
    val historial: HistorialEndosos,
    val metadatos: MetadatosSincronizacion
)

/**
 * Puerto de almacenamiento local para la HU08.
 *
 * La implementación Android debe cifrar la información en reposo y reemplazar de forma
 * atómica la instantánea del usuario. Ninguna lectura puede devolver datos de otra clave.
 */
interface CachePolizas {
    suspend fun reemplazar(
        usuario: ClaveUsuarioCache,
        billetera: Billetera,
        certificados: List<Certificado>,
        sincronizadaEnMs: Long
    )

    suspend fun billetera(usuario: ClaveUsuarioCache): BilleteraCacheada?

    suspend fun certificado(
        usuario: ClaveUsuarioCache,
        polizaId: String
    ): CertificadoCacheado?

    suspend fun historialEndosos(
        usuario: ClaveUsuarioCache,
        polizaId: String
    ): HistorialEndososCacheado?

    /** Actualiza el historial sin descartar la billetera ni los certificados ya cifrados. */
    suspend fun guardarHistorialEndosos(
        usuario: ClaveUsuarioCache,
        polizaId: String,
        historial: HistorialEndosos
    )

    suspend fun eliminar(usuario: ClaveUsuarioCache)

    /** Defensa adicional para logout o recuperación ante una caché inconsistente. */
    suspend fun eliminarTodo()
}
