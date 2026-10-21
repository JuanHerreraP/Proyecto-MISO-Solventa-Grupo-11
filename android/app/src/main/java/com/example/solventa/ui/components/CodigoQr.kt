package com.example.solventa.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.google.zxing.BarcodeFormat
import com.google.zxing.EncodeHintType
import com.google.zxing.WriterException
import com.google.zxing.qrcode.QRCodeWriter
import com.google.zxing.qrcode.decoder.ErrorCorrectionLevel

/** Módulos del QR como matriz de booleanos (true = oscuro). Se genera en el dispositivo. */
fun matrizQr(contenido: String): List<List<Boolean>>? = try {
    val matriz = QRCodeWriter().encode(
        contenido,
        BarcodeFormat.QR_CODE,
        0,
        0,
        mapOf(
            EncodeHintType.MARGIN to 1,
            EncodeHintType.ERROR_CORRECTION to ErrorCorrectionLevel.M,
            EncodeHintType.CHARACTER_SET to "UTF-8"
        )
    )
    List(matriz.height) { y -> List(matriz.width) { x -> matriz.get(x, y) } }
} catch (error: WriterException) {
    null
} catch (error: IllegalArgumentException) {
    null
}

/**
 * Dibuja el QR con Canvas, sin bitmaps, para que se vea nítido en cualquier densidad.
 * Fondo blanco siempre: los lectores necesitan contraste aunque la app esté en modo oscuro.
 */
@Composable
fun SolventaCodigoQr(
    contenido: String,
    descripcion: String,
    modifier: Modifier = Modifier,
    tamano: Dp = 200.dp
) {
    val modulos = remember(contenido) { matrizQr(contenido) } ?: return
    Box(
        modifier = modifier
            .size(tamano)
            .background(Color.White)
            .padding(8.dp)
            .semantics { contentDescription = descripcion }
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val lado = size.minDimension / modulos.size
            modulos.forEachIndexed { y, fila ->
                fila.forEachIndexed { x, oscuro ->
                    if (oscuro) {
                        drawRect(
                            color = Color.Black,
                            topLeft = Offset(x * lado, y * lado),
                            // Un poco más grande para que no queden líneas entre módulos.
                            size = Size(lado + 0.5f, lado + 0.5f)
                        )
                    }
                }
            }
        }
    }
}
