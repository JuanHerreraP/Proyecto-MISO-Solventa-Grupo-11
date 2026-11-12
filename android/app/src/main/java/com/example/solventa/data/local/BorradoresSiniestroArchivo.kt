package com.example.solventa.data.local

import android.content.Context
import com.example.solventa.domain.siniestros.BorradorSiniestro
import com.example.solventa.domain.siniestros.BorradoresSiniestro
import com.example.solventa.domain.siniestros.EvidenciaLocal
import com.google.gson.Gson
import java.io.File
import java.io.IOException
import java.security.MessageDigest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Borrador del reporte de siniestro en el almacenamiento privado de la app (HU04).
 *
 * Cada usuario tiene su carpeta, nombrada con el SHA-256 de su identificador para no guardar
 * datos personales en la ruta: `borradores_siniestro/<hash>/borrador.json` y las fotos o videos
 * en `borradores_siniestro/<hash>/evidencias/`. Solo la app puede leerlos y se borran cuando el
 * reporte termina de enviarse o el cliente lo descarta.
 */
class BorradoresSiniestroArchivo(
    private val raiz: File,
    private val gson: Gson = Gson()
) : BorradoresSiniestro {

    constructor(context: Context) : this(File(context.applicationContext.filesDir, DIRECTORIO))

    override suspend fun leer(usuarioId: String): BorradorSiniestro? = withContext(Dispatchers.IO) {
        val archivo = archivoBorrador(usuarioId)
        if (!archivo.isFile) return@withContext null
        try {
            gson.fromJson(archivo.readText(Charsets.UTF_8), BorradorSiniestro::class.java)
                ?.takeIf { it.esValido() }
                ?: error("Borrador incompleto.")
        } catch (error: Exception) {
            // Un borrador ilegible no debe bloquear al cliente: se descarta.
            archivo.delete()
            null
        }
    }

    override suspend fun guardar(usuarioId: String, borrador: BorradorSiniestro) {
        withContext(Dispatchers.IO) {
            val destino = archivoBorrador(usuarioId)
            val carpeta = destino.parentFile ?: throw IOException("Ruta de borrador inválida.")
            carpeta.mkdirs()
            // Se escribe aparte y se reemplaza: un cierre a mitad no deja un borrador corrupto.
            val temporal = File(carpeta, "$ARCHIVO_BORRADOR.tmp")
            temporal.writeText(gson.toJson(borrador), Charsets.UTF_8)
            if (!temporal.renameTo(destino)) {
                destino.delete()
                if (!temporal.renameTo(destino)) {
                    throw IOException("No se pudo guardar el borrador del siniestro.")
                }
            }
        }
    }

    override suspend fun eliminar(usuarioId: String) {
        withContext(Dispatchers.IO) { directorioUsuario(usuarioId).deleteRecursively() }
    }

    override suspend fun eliminarArchivo(evidencia: EvidenciaLocal) {
        withContext(Dispatchers.IO) {
            val archivo = File(evidencia.rutaArchivo)
            // Solo se borran archivos propios de los borradores.
            if (archivo.canonicalPath.startsWith(raiz.canonicalPath + File.separator)) {
                archivo.delete()
            }
        }
    }

    /** Carpeta donde se guardan las fotos y videos del borrador de este usuario. */
    fun directorioEvidencias(usuarioId: String): File =
        File(directorioUsuario(usuarioId), DIRECTORIO_EVIDENCIAS).apply { mkdirs() }

    private fun archivoBorrador(usuarioId: String) =
        File(directorioUsuario(usuarioId), ARCHIVO_BORRADOR)

    private fun directorioUsuario(usuarioId: String): File {
        require(usuarioId.isNotBlank()) { "El usuario no puede estar vacío." }
        val hash = MessageDigest.getInstance("SHA-256")
            .digest(usuarioId.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }
        return File(raiz, hash)
    }

    /** Gson no pasa por el constructor de Kotlin: un campo ausente llega como null. */
    @Suppress("SENSELESS_COMPARISON")
    private fun BorradorSiniestro.esValido(): Boolean =
        id != null && evidencias != null && evidencias.all { it != null && it.rutaArchivo != null }

    companion object {
        const val DIRECTORIO = "borradores_siniestro"
        private const val ARCHIVO_BORRADOR = "borrador.json"
        private const val DIRECTORIO_EVIDENCIAS = "evidencias"
    }
}
