package com.example.solventa.ui.siniestros

import android.content.ActivityNotFoundException
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import com.example.solventa.data.local.ArchivosEvidencia
import com.example.solventa.data.local.ProveedorUbicacion
import com.example.solventa.domain.siniestros.EvidenciaImportada
import com.example.solventa.domain.siniestros.TipoEvidencia
import java.io.File
import kotlinx.coroutines.launch

/** Lo que el formulario puede pedir: abrir la cámara, grabar video o elegir de la galería. */
class AccionesEvidencia(
    val tomarFoto: () -> Unit,
    val grabarVideo: () -> Unit,
    val elegirArchivo: () -> Unit
)

private const val SIN_CAMARA = "No encontramos una app de cámara en el dispositivo."

/**
 * Conecta el formulario de siniestro con la cámara, la galería y la ubicación (HU04).
 *
 * - Al abrir el formulario pide una vez el permiso de ubicación. Si el cliente no lo concede,
 *   las evidencias se adjuntan sin geoetiqueta y el coordinador se lo informa.
 * - La cámara escribe directo en la carpeta privada del borrador; la ruta se conserva aunque
 *   Android cierre la app mientras la cámara está abierta.
 * - Al volver de la cámara se toma la ubicación del momento y se calcula la huella del archivo.
 */
@Composable
fun rememberCapturaEvidencias(
    usuarioId: String?,
    archivos: ArchivosEvidencia,
    ubicacion: ProveedorUbicacion,
    onEvidencia: (EvidenciaImportada, Boolean) -> Unit
): AccionesEvidencia {
    val alcance = rememberCoroutineScope()
    val alRecibir by rememberUpdatedState(onEvidencia)
    var archivoPendiente by rememberSaveable { mutableStateOf<String?>(null) }
    var tipoPendiente by rememberSaveable { mutableStateOf<String?>(null) }
    var permisoPedido by rememberSaveable { mutableStateOf(false) }

    val pedirUbicacion = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { }

    LaunchedEffect(Unit) {
        if (!permisoPedido && !ubicacion.tienePermiso()) {
            permisoPedido = true
            pedirUbicacion.launch(ProveedorUbicacion.PERMISOS)
        }
    }

    fun terminarCaptura(exito: Boolean) {
        val ruta = archivoPendiente
        val tipoContenido = tipoPendiente
        archivoPendiente = null
        tipoPendiente = null
        if (ruta == null || tipoContenido == null) return
        val archivo = File(ruta)
        if (!exito) {
            archivo.delete()
            return
        }
        alcance.launch {
            val resultado = archivos.desdeCaptura(archivo, tipoContenido, ubicacion.ultimaUbicacion())
            alRecibir(resultado, false)
        }
    }

    val camaraFoto = rememberLauncherForActivityResult(
        ActivityResultContracts.TakePicture()
    ) { exito -> terminarCaptura(exito) }

    val camaraVideo = rememberLauncherForActivityResult(
        ActivityResultContracts.CaptureVideo()
    ) { exito -> terminarCaptura(exito) }

    val galeria = rememberLauncherForActivityResult(
        ActivityResultContracts.PickVisualMedia()
    ) { uri ->
        val usuario = usuarioId
        if (uri != null && usuario != null) {
            alcance.launch { alRecibir(archivos.importar(uri, usuario), true) }
        }
    }

    fun capturar(tipo: TipoEvidencia) {
        val usuario = usuarioId ?: return
        val archivo = archivos.nuevoArchivoCaptura(usuario, tipo)
        archivoPendiente = archivo.absolutePath
        tipoPendiente = if (tipo == TipoEvidencia.FOTO) "image/jpeg" else "video/mp4"
        try {
            val uri = archivos.uriPara(archivo)
            if (tipo == TipoEvidencia.FOTO) camaraFoto.launch(uri) else camaraVideo.launch(uri)
        } catch (error: ActivityNotFoundException) {
            archivoPendiente = null
            tipoPendiente = null
            archivo.delete()
            alRecibir(EvidenciaImportada.Rechazada(SIN_CAMARA), false)
        }
    }

    return remember(usuarioId) {
        AccionesEvidencia(
            tomarFoto = { capturar(TipoEvidencia.FOTO) },
            grabarVideo = { capturar(TipoEvidencia.VIDEO) },
            elegirArchivo = {
                galeria.launch(
                    PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageAndVideo)
                )
            }
        )
    }
}
