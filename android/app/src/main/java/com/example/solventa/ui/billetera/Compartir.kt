package com.example.solventa.ui.billetera

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import com.example.solventa.domain.polizas.EnlaceCompartido
import com.example.solventa.domain.polizas.Formatos

/** Texto que acompaña el enlace temporal del certificado. */
fun textoParaCompartir(numeroPoliza: String?, enlace: EnlaceCompartido): String {
    val poliza = numeroPoliza?.let { " $it" }.orEmpty()
    val vence = enlace.expiraEn.takeIf { it.isNotBlank() }?.let { " (válido hasta el ${Formatos.fechaHora(it)})" }
    return "Certificado de mi póliza$poliza en Solventa: ${enlace.url}${vence.orEmpty()}"
}

/** Abre el menú del sistema para compartir. Devuelve false si no hay apps para hacerlo. */
fun Context.compartirTexto(texto: String, titulo: String = "Compartir certificado"): Boolean {
    val envio = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(Intent.EXTRA_TEXT, texto)
    }
    return try {
        startActivity(Intent.createChooser(envio, titulo).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        true
    } catch (error: ActivityNotFoundException) {
        false
    }
}
