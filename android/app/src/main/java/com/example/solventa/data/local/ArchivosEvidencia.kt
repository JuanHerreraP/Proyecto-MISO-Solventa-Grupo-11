package com.example.solventa.data.local

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import android.net.Uri
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import com.example.solventa.domain.siniestros.EvidenciaImportada
import com.example.solventa.domain.siniestros.EvidenciaLocal
import com.example.solventa.domain.siniestros.MensajesSiniestros
import com.example.solventa.domain.siniestros.ReglasEvidencia
import com.example.solventa.domain.siniestros.TipoEvidencia
import com.example.solventa.domain.siniestros.Ubicacion
import java.io.File
import java.io.InputStream
import java.io.OutputStream
import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.UUID
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Prepara las fotos y videos del reporte de siniestro (HU04).
 *
 * Los archivos se guardan en la carpeta privada del borrador del usuario, se calcula su huella
 * SHA-256 y se registra la fecha y hora de captura. La cámara escribe directo en esa carpeta a
 * través del FileProvider de la app; lo que viene de la galería se copia, con un tope para no
 * llenar el almacenamiento con un archivo que de todos modos sería rechazado.
 */
class ArchivosEvidencia(
    private val context: Context,
    private val borradores: BorradoresSiniestroArchivo,
    private val reloj: () -> Long = { System.currentTimeMillis() }
) {

    /** Archivo vacío donde la cámara escribirá la foto o el video. */
    fun nuevoArchivoCaptura(usuarioId: String, tipo: TipoEvidencia): File {
        val extension = if (tipo == TipoEvidencia.FOTO) "jpg" else "mp4"
        return File(borradores.directorioEvidencias(usuarioId), "${UUID.randomUUID()}.$extension")
    }

    fun uriPara(archivo: File): Uri =
        FileProvider.getUriForFile(context, "${context.packageName}.archivos", archivo)

    /** Evidencia a partir de lo que dejó la cámara, con la ubicación del momento si la hay. */
    suspend fun desdeCaptura(
        archivo: File,
        tipoContenido: String,
        ubicacion: Ubicacion?
    ): EvidenciaImportada = withContext(Dispatchers.IO) {
        if (!archivo.isFile || archivo.length() == 0L) {
            archivo.delete()
            return@withContext EvidenciaImportada.Rechazada(MensajesSiniestros.ARCHIVO_VACIO)
        }
        EvidenciaImportada.Lista(
            construir(archivo, tipoContenido, ubicacion, capturadaEn = isoUtc(reloj()))
        )
    }

    /**
     * Copia un archivo elegido de la galería. No lleva ubicación: no se sabe dónde se tomó, y la
     * ubicación actual del teléfono no sería la del evento.
     */
    suspend fun importar(uri: Uri, usuarioId: String): EvidenciaImportada =
        withContext(Dispatchers.IO) {
            val tipoContenido = context.contentResolver.getType(uri)
            val tipo = ReglasEvidencia.tipoDe(tipoContenido)
                ?: return@withContext EvidenciaImportada.Rechazada(
                    MensajesSiniestros.FORMATO_NO_PERMITIDO
                )
            val limite = ReglasEvidencia.limiteDe(tipo)
            val extension = when (tipoContenido?.substringBefore(';')?.trim()?.lowercase()) {
                "image/png" -> "png"
                "video/3gpp" -> "3gp"
                "video/mp4" -> "mp4"
                else -> "jpg"
            }
            val destino = File(
                borradores.directorioEvidencias(usuarioId),
                "${UUID.randomUUID()}.$extension"
            )
            val leidos: Long? = try {
                context.contentResolver.openInputStream(uri)?.use { entrada ->
                    destino.outputStream().use { salida -> copiarConLimite(entrada, salida, limite) }
                }
            } catch (error: Exception) {
                null
            }
            val copiados: Long = leidos ?: run {
                destino.delete()
                return@withContext EvidenciaImportada.Rechazada(
                    MensajesSiniestros.ARCHIVO_LOCAL_AUSENTE
                )
            }
            when {
                copiados > limite -> {
                    destino.delete()
                    EvidenciaImportada.Rechazada(MensajesSiniestros.ARCHIVO_DEMASIADO_GRANDE)
                }
                copiados == 0L -> {
                    destino.delete()
                    EvidenciaImportada.Rechazada(MensajesSiniestros.ARCHIVO_VACIO)
                }
                else -> EvidenciaImportada.Lista(
                    construir(destino, tipoContenido.orEmpty(), ubicacion = null, capturadaEn = null)
                )
            }
        }

    private fun construir(
        archivo: File,
        tipoContenido: String,
        ubicacion: Ubicacion?,
        capturadaEn: String?
    ): EvidenciaLocal {
        val normalizado = tipoContenido.substringBefore(';').trim().lowercase()
        return EvidenciaLocal(
            id = UUID.randomUUID().toString(),
            rutaArchivo = archivo.absolutePath,
            tipoContenido = normalizado,
            tipo = ReglasEvidencia.tipoDe(normalizado) ?: TipoEvidencia.FOTO,
            tamanoBytes = archivo.length(),
            huellaSha256 = huellaSha256(archivo),
            capturadaEn = capturadaEn,
            ubicacion = ubicacion,
            nombreArchivo = archivo.name
        )
    }

    companion object {
        /** Copia hasta superar el límite por un byte; devuelve cuántos bytes copió. */
        fun copiarConLimite(entrada: InputStream, salida: OutputStream, limite: Long): Long {
            val buffer = ByteArray(64 * 1024)
            var total = 0L
            while (total <= limite) {
                val leidos = entrada.read(buffer)
                if (leidos < 0) break
                salida.write(buffer, 0, leidos)
                total += leidos
            }
            return total
        }

        fun huellaSha256(archivo: File): String {
            val digest = MessageDigest.getInstance("SHA-256")
            archivo.inputStream().use { entrada ->
                val buffer = ByteArray(64 * 1024)
                while (true) {
                    val leidos = entrada.read(buffer)
                    if (leidos < 0) break
                    digest.update(buffer, 0, leidos)
                }
            }
            return digest.digest().joinToString("") { "%02x".format(it) }
        }

        /** ISO 8601 en UTC; `java.time` no está disponible en API 24 sin desugaring. */
        fun isoUtc(millis: Long): String =
            SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
                .apply { timeZone = TimeZone.getTimeZone("UTC") }
                .format(Date(millis))
    }
}

/**
 * Ubicación del teléfono al capturar una evidencia, solo si el cliente dio el permiso.
 * Usa la última ubicación conocida de los proveedores activos, sin servicios de Google.
 */
class ProveedorUbicacion(private val context: Context) {

    fun tienePermiso(): Boolean =
        concedido(Manifest.permission.ACCESS_FINE_LOCATION) ||
            concedido(Manifest.permission.ACCESS_COARSE_LOCATION)

    @SuppressLint("MissingPermission") // El permiso se verifica en tienePermiso().
    fun ultimaUbicacion(): Ubicacion? {
        if (!tienePermiso()) return null
        val gestor = context.getSystemService(Context.LOCATION_SERVICE) as? LocationManager
            ?: return null
        val ultima: Location? = try {
            gestor.getProviders(true)
                .mapNotNull { proveedor -> gestor.getLastKnownLocation(proveedor) }
                .maxByOrNull { it.time }
        } catch (error: SecurityException) {
            null
        }
        return ultima?.let {
            Ubicacion(
                latitud = it.latitude,
                longitud = it.longitude,
                precisionMetros = if (it.hasAccuracy()) it.accuracy else null
            )
        }
    }

    private fun concedido(permiso: String): Boolean =
        ContextCompat.checkSelfPermission(context, permiso) == PackageManager.PERMISSION_GRANTED

    companion object {
        val PERMISOS = arrayOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION
        )
    }
}
