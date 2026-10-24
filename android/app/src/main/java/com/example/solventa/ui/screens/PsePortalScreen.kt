package com.example.solventa.ui.screens

import android.annotation.SuppressLint
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.net.toUri
import com.example.solventa.ui.theme.Navegacion

/**
 * Portal PSE simulado dentro de la app. Carga en un WebView la URL que devolvió el backend
 * y, cuando el banco redirige a la URL de retorno (que lleva ?pago=...), avisa para continuar
 * el flujo sin salir de la aplicación.
 */
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun PsePortalScreen(
    url: String,
    urlRetorno: String,
    onRetorno: (pagoId: String) -> Unit,
    onVolver: () -> Unit,
    modifier: Modifier = Modifier
) {
    var cargando by remember { mutableStateOf(true) }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets(0, 0, 0, 0)
    ) { paddingValues ->
        Column(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = onVolver) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = "Volver",
                        tint = MaterialTheme.colorScheme.onSurface
                    )
                }
                Text(
                    text = "Pago con PSE",
                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                    color = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.weight(1f)
                )
            }
            Box(modifier = Modifier.fillMaxSize()) {
                AndroidView(
                    modifier = Modifier.fillMaxSize(),
                    factory = { contexto ->
                        WebView(contexto).apply {
                            settings.javaScriptEnabled = true
                            settings.domStorageEnabled = true
                            webViewClient = object : WebViewClient() {
                                override fun shouldOverrideUrlLoading(
                                    view: WebView?,
                                    request: WebResourceRequest?
                                ): Boolean {
                                    val destino = request?.url?.toString() ?: return false
                                    return interceptarRetorno(destino, urlRetorno, onRetorno)
                                }

                                override fun onPageFinished(view: WebView?, url: String?) {
                                    cargando = false
                                }
                            }
                            loadUrl(url)
                        }
                    }
                )
                if (cargando) {
                    CircularProgressIndicator(
                        color = Navegacion,
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
            }
        }
    }
}

/** Devuelve true (y avisa el retorno) si la URL es la de retorno del banco con el pago. */
private fun interceptarRetorno(
    destino: String,
    urlRetorno: String,
    onRetorno: (String) -> Unit
): Boolean {
    if (!destino.startsWith(urlRetorno)) return false
    val pagoId = destino.toUri().getQueryParameter("pago")
    if (pagoId != null) {
        onRetorno(pagoId)
        return true
    }
    return false
}
