package com.example.solventa.ui.billetera

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import com.example.solventa.domain.polizas.EnlaceCompartido
import com.example.solventa.domain.polizas.Formatos
import com.example.solventa.R
import com.example.solventa.i18n.tr

/** Texto que acompaña el enlace temporal del certificado. */
fun textoParaCompartir(numeroPoliza: String?, enlace: EnlaceCompartido): String {
    val poliza = numeroPoliza?.let { " $it" }.orEmpty()
    val vence = enlace.expiraEn.takeIf { it.isNotBlank() }?.let { tr(R.string.compartir_valido_hasta_el, Formatos.fechaHora(it)) }
    return tr(R.string.compartir_certificado_de_mi_poliza_en, poliza, enlace.url, vence.orEmpty())
}

/** Abre el menú del sistema para compartir. Devuelve false si no hay apps para hacerlo. */
fun Context.compartirTexto(texto: String, titulo: String = tr(R.string.certificate_compartir_certificado)): Boolean {
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
