package com.example.solventa.ui.billetera

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import androidx.core.content.FileProvider
import com.example.solventa.domain.polizas.DocumentoPoliza
import java.io.File
import java.io.IOException

/** Guarda temporalmente el PDF validado y lo entrega en modo lectura a una app externa. */
fun Context.abrirDocumento(documento: DocumentoPoliza): Boolean = try {
    val directorio = File(cacheDir, "polizas").apply { mkdirs() }
    val nombre = documento.nombreArchivo
        .substringAfterLast('/')
        .substringAfterLast('\\')
        .takeIf { it.endsWith(".pdf", ignoreCase = true) }
        ?: "poliza.pdf"
    val archivo = File(directorio, nombre).apply {
        writeBytes(documento.contenido)
    }
    val uri = FileProvider.getUriForFile(this, "$packageName.archivos", archivo)
    val intent = Intent(Intent.ACTION_VIEW).apply {
        setDataAndType(uri, "application/pdf")
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
    }
    startActivity(intent)
    true
} catch (error: ActivityNotFoundException) {
    false
} catch (error: IOException) {
    false
} catch (error: IllegalArgumentException) {
    false
} catch (error: SecurityException) {
    false
}

/** Elimina únicamente los PDF temporales al cerrar o cambiar la sesión. */
fun Context.eliminarDocumentosTemporales() {
    try {
        File(cacheDir, "polizas").deleteRecursively()
    } catch (error: SecurityException) {
        // La caché del sistema se puede volver a limpiar en el siguiente cierre de sesión.
    }
}
