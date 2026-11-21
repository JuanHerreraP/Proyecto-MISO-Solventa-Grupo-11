package com.example.solventa.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.polizas.Formatos
import com.example.solventa.domain.siniestros.EstadoSiniestro
import com.example.solventa.domain.siniestros.OrigenSiniestro
import com.example.solventa.domain.siniestros.Siniestro
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.SolventaTheme

/**
 * Detalle de un siniestro con su estado actual (HU05): al tocar una notificación de cambio de
 * estado o de pago paramétrico se abre aquí, ya actualizado. También se llega desde la lista.
 */
@Composable
fun ClaimDetailScreen(
    siniestro: Siniestro?,
    cargando: Boolean,
    error: String?,
    onReintentar: () -> Unit,
    onVolver: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
        Column(modifier = Modifier.fillMaxSize()) {
            Encabezado(titulo = "Detalle del siniestro", onVolver = onVolver)

            when {
                siniestro == null && cargando -> Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(
                        color = Navegacion,
                        modifier = Modifier.semantics {
                            contentDescription = "Cargando el siniestro"
                        }
                    )
                }

                siniestro == null -> Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = error ?: "No encontramos ese siniestro en tu cuenta.",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.size(16.dp))
                    SolventaPrimaryButton(text = "Reintentar", onClick = onReintentar)
                }

                else -> Contenido(siniestro = siniestro, error = error)
            }
        }
    }
}

@Composable
private fun Contenido(siniestro: Siniestro, error: String?) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp)
            .padding(bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                text = "Póliza ${siniestro.polizaId}",
                style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.onSurface
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                EtiquetaEstadoSiniestro(siniestro.estado)
                Spacer(modifier = Modifier.width(8.dp))
                EtiquetaOrigen(siniestro.origen)
            }
            // El estado se refresca al abrir; si no se pudo, se avisa sin esconder lo que ya hay.
            if (error != null) {
                Text(
                    text = error,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.error
                )
            }
        }

        Seccion("Estado") {
            Text(
                text = mensajeDelEstado(siniestro),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface
            )
            siniestro.montoAprobado?.takeIf { it.isNotBlank() }?.let {
                Dato("Monto aprobado", Formatos.dinero(it, siniestro.moneda))
            }
            siniestro.evaluadoEn?.takeIf { it.isNotBlank() }?.let {
                Dato("Fecha de la decisión", Formatos.fechaHora(it))
            }
            siniestro.motivoRechazo?.takeIf { it.isNotBlank() }?.let {
                Dato("Motivo", it)
            }
        }

        Seccion("Lo que reportaste") {
            Dato("Fecha del evento", Formatos.fecha(siniestro.fechaEvento))
            siniestro.tipoSiniestro?.let { Dato("Tipo de siniestro", it.etiqueta) }
            siniestro.lugar.takeIf { it.isNotBlank() }?.let { Dato("Lugar", it) }
            siniestro.descripcion.takeIf { it.isNotBlank() }?.let { Dato("Descripción", it) }
            siniestro.estimacionDanos.takeIf { it.isNotBlank() }?.let {
                Dato("Estimación de daños", Formatos.dinero(it, siniestro.moneda))
            }
            Dato("Registrado", Formatos.fechaHora(siniestro.registradoEn))
        }
    }
}

private fun mensajeDelEstado(siniestro: Siniestro): String = when (siniestro.estado) {
    EstadoSiniestro.REGISTRADO -> "Recibimos tu siniestro. Pronto empezaremos a revisarlo."
    EstadoSiniestro.EN_EVALUACION -> "Estamos evaluando tu siniestro."
    EstadoSiniestro.APROBADO ->
        if (siniestro.origen == OrigenSiniestro.AUTOMATICO) {
            "Aprobamos automáticamente el pago de tu seguro paramétrico."
        } else {
            "Aprobamos tu siniestro."
        }
    EstadoSiniestro.RECHAZADO -> "No pudimos aprobar tu siniestro."
}

@Composable
private fun Seccion(titulo: String, contenido: @Composable () -> Unit) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = titulo,
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
            contenido()
        }
    }
}

@Composable
private fun Dato(etiqueta: String, valor: String) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(
            text = etiqueta,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
        )
        Text(
            text = valor,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurface
        )
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun ClaimDetailScreenPreview() {
    SolventaTheme {
        ClaimDetailScreen(
            siniestro = Siniestro(
                siniestroId = "SIN-1",
                polizaId = "SOL-PM-000001",
                origen = OrigenSiniestro.AUTOMATICO,
                estado = EstadoSiniestro.APROBADO,
                eventoId = "EV-1",
                fechaEvento = "2026-10-20",
                horaEvento = "18:30:00",
                lugar = "Aeropuerto El Dorado",
                descripcion = "Retraso de vuelo superior al umbral contratado.",
                estimacionDanos = "500000.00",
                moneda = "COP",
                registradoEn = "2026-10-20T23:00:00Z",
                montoAprobado = "500000.00",
                evaluadoEn = "2026-10-20T23:00:05Z"
            ),
            cargando = false,
            error = null,
            onReintentar = {},
            onVolver = {}
        )
    }
}
