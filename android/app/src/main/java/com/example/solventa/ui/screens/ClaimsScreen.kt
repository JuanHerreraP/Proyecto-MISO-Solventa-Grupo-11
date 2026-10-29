package com.example.solventa.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.polizas.Formatos
import com.example.solventa.domain.siniestros.EstadoSiniestro
import com.example.solventa.domain.siniestros.OrigenSiniestro
import com.example.solventa.domain.siniestros.Siniestro
import com.example.solventa.domain.siniestros.Siniestros
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.theme.Atencion
import com.example.solventa.ui.theme.Avance
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.SolventaTheme

/** Lista de siniestros del cliente (HU20): manuales y automáticos de telemetría. */
@Composable
fun ClaimsScreen(
    siniestros: Siniestros?,
    cargando: Boolean,
    error: String?,
    onReintentar: () -> Unit,
    onVolver: () -> Unit,
    onReportar: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
        Column(modifier = Modifier.fillMaxSize()) {
            Encabezado(titulo = "Mis siniestros", onVolver = onVolver)

            when {
                siniestros == null && cargando -> CentradoClaims {
                    CircularProgressIndicator(
                        color = Navegacion,
                        modifier = Modifier.semantics { contentDescription = "Cargando tus siniestros" }
                    )
                }

                siniestros == null && error != null -> CentradoClaims {
                    Text(
                        text = error,
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.size(16.dp))
                    SolventaPrimaryButton(text = "Reintentar", onClick = onReintentar)
                }

                siniestros == null || siniestros.vacia -> CentradoClaims {
                    Text(
                        text = "Aún no tienes siniestros",
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.size(8.dp))
                    Text(
                        text = "Aquí verás los siniestros que reportes y los que Solventa detecte automáticamente.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                    )
                    Spacer(modifier = Modifier.size(16.dp))
                    SolventaPrimaryButton(text = "Reportar siniestro", onClick = onReportar)
                }

                else -> ListaSiniestros(siniestros = siniestros, error = error, onReportar = onReportar)
            }
        }
    }
}

@Composable
private fun ListaSiniestros(siniestros: Siniestros, error: String?, onReportar: () -> Unit) {
    LazyColumn(
        contentPadding = PaddingValues(start = 24.dp, end = 24.dp, top = 8.dp, bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        if (error != null) {
            item {
                Text(text = error, style = MaterialTheme.typography.bodyMedium, color = Atencion)
            }
        }
        item {
            Text(
                text = "${siniestros.total} en total · ${siniestros.automaticos} automáticos",
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
            )
        }
        items(siniestros.siniestros, key = { it.siniestroId }) { siniestro ->
            TarjetaSiniestro(siniestro)
        }
        item {
            Spacer(modifier = Modifier.size(4.dp))
            SolventaPrimaryButton(text = "Reportar siniestro", onClick = onReportar)
        }
    }
}

@Composable
private fun TarjetaSiniestro(siniestro: Siniestro) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = "Póliza ${siniestro.polizaId}",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.weight(1f, fill = false)
                )
                Spacer(modifier = Modifier.width(8.dp))
                EtiquetaOrigen(siniestro.origen)
                Spacer(modifier = Modifier.width(6.dp))
                EtiquetaEstadoSiniestro(siniestro.estado)
            }
            Text(
                text = "Evento: ${Formatos.fecha(siniestro.fechaEvento)}" +
                    if (siniestro.lugar.isNotBlank()) " · ${siniestro.lugar}" else "",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
            if (siniestro.descripcion.isNotBlank()) {
                Text(
                    text = siniestro.descripcion,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.85f)
                )
            }
            if (siniestro.estimacionDanos.isNotBlank()) {
                Text(
                    text = "Estimación: ${Formatos.dinero(siniestro.estimacionDanos, siniestro.moneda)}",
                    style = MaterialTheme.typography.labelMedium,
                    color = Navegacion
                )
            }
        }
    }
}

/** El texto distingue el origen: el color nunca es la única señal. */
@Composable
private fun EtiquetaOrigen(origen: OrigenSiniestro) {
    val (fondo, texto, etiqueta) = when (origen) {
        OrigenSiniestro.AUTOMATICO -> Triple(Navegacion.copy(alpha = 0.15f), Navegacion, "Automático")
        OrigenSiniestro.MANUAL -> Triple(
            Color(0xFF8A8F98).copy(alpha = 0.2f), Color(0xFF3A3D42), "Manual"
        )
    }
    Surface(shape = RoundedCornerShape(8.dp), color = fondo) {
        Text(
            text = etiqueta,
            style = MaterialTheme.typography.labelMedium,
            color = texto,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
        )
    }
}

@Composable
private fun EtiquetaEstadoSiniestro(estado: EstadoSiniestro) {
    val (fondo, texto, etiqueta) = when (estado) {
        EstadoSiniestro.REGISTRADO -> Triple(Avance.copy(alpha = 0.25f), Color(0xFF2F5A0B), "Registrado")
        EstadoSiniestro.EN_EVALUACION ->
            Triple(Atencion.copy(alpha = 0.2f), Color(0xFF7A3A05), "En evaluación")
        EstadoSiniestro.APROBADO -> Triple(Avance.copy(alpha = 0.25f), Color(0xFF2F5A0B), "Aprobado")
        EstadoSiniestro.RECHAZADO ->
            Triple(Color(0xFFB00020).copy(alpha = 0.15f), Color(0xFF7A0012), "Rechazado")
    }
    Surface(shape = RoundedCornerShape(8.dp), color = fondo) {
        Text(
            text = etiqueta,
            style = MaterialTheme.typography.labelMedium,
            color = texto,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
        )
    }
}

@Composable
private fun CentradoClaims(contenido: @Composable () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) { contenido() }
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun ClaimsScreenPreview() {
    val lista = Siniestros(
        listOf(
            Siniestro(
                siniestroId = "SIN-1",
                polizaId = "DEMO-04",
                origen = OrigenSiniestro.AUTOMATICO,
                estado = EstadoSiniestro.REGISTRADO,
                eventoId = "FLIGHT-AV123-20261026-abc",
                fechaEvento = "2026-10-26",
                horaEvento = "20:00:00",
                lugar = "BOG",
                descripcion = "Siniestro paramétrico automático por evento RETRASO_VUELO.",
                estimacionDanos = "500000.00",
                moneda = "COP",
                registradoEn = "2026-10-26T20:01:00Z"
            )
        )
    )
    SolventaTheme {
        ClaimsScreen(
            siniestros = lista,
            cargando = false,
            error = null,
            onReintentar = {},
            onVolver = {}
        )
    }
}
