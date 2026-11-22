package com.example.solventa.ui.screens

import androidx.compose.foundation.BorderStroke
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircleOutline
import androidx.compose.material.icons.outlined.Cancel
import androidx.compose.material.icons.outlined.RadioButtonUnchecked
import androidx.compose.material.icons.outlined.Schedule
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.polizas.Formatos
import com.example.solventa.domain.siniestros.EstadoSiniestro
import com.example.solventa.domain.siniestros.OrigenSiniestro
import com.example.solventa.domain.siniestros.Siniestro
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.Sincronizado
import com.example.solventa.ui.theme.SolventaTheme

/** En qué punto está cada paso del caso. */
internal enum class AvancePaso { HECHO, EN_CURSO, PENDIENTE, RECHAZADO }

internal data class PasoSiniestro(
    val titulo: String,
    val detalle: String,
    val avance: AvancePaso
)

/** Cuánto del caso ya se recorrió, de 0 a 1. */
internal fun progresoDelCaso(estado: EstadoSiniestro): Float = when (estado) {
    EstadoSiniestro.REGISTRADO -> 0.2f
    EstadoSiniestro.EN_EVALUACION -> 0.6f
    EstadoSiniestro.APROBADO, EstadoSiniestro.RECHAZADO -> 1f
}

/**
 * Los pasos del caso según su origen y estado. Solo se muestran fechas que el backend entrega:
 * el registro y la decisión.
 */
internal fun pasosDelCaso(siniestro: Siniestro): List<PasoSiniestro> {
    val registrado = Formatos.fechaHora(siniestro.registradoEn)
    val decidido = siniestro.evaluadoEn?.takeIf { it.isNotBlank() }?.let(Formatos::fechaHora)
    val automatico = siniestro.origen == OrigenSiniestro.AUTOMATICO
    val avanzado = siniestro.estado != EstadoSiniestro.REGISTRADO

    val primero = PasoSiniestro(
        if (automatico) "Evento detectado" else "Reporte recibido",
        registrado,
        AvancePaso.HECHO
    )
    val segundo = if (automatico) {
        PasoSiniestro(
            "Evaluación automática",
            if (avanzado) "Evaluado según las condiciones de tu póliza" else "Se evalúa en segundos",
            if (avanzado) AvancePaso.HECHO else AvancePaso.EN_CURSO
        )
    } else {
        PasoSiniestro(
            "Evidencias validadas",
            if (avanzado) "Revisión completada" else "Pendiente de revisión",
            if (avanzado) AvancePaso.HECHO else AvancePaso.EN_CURSO
        )
    }
    val tercero = when (siniestro.estado) {
        EstadoSiniestro.REGISTRADO -> PasoSiniestro(
            "Evaluación", "Recibirás una notificación", AvancePaso.PENDIENTE
        )
        EstadoSiniestro.EN_EVALUACION -> PasoSiniestro(
            "Evaluación en curso", "Recibirás una notificación", AvancePaso.EN_CURSO
        )
        EstadoSiniestro.APROBADO -> PasoSiniestro(
            if (automatico) "Pago aprobado" else "Siniestro aprobado",
            listOfNotNull(
                siniestro.montoAprobado?.takeIf { it.isNotBlank() }
                    ?.let { "Monto aprobado ${Formatos.dinero(it, siniestro.moneda)}" },
                decidido
            ).joinToString(" · ").ifBlank { "Aprobado" },
            AvancePaso.HECHO
        )
        EstadoSiniestro.RECHAZADO -> PasoSiniestro(
            "Siniestro rechazado",
            listOfNotNull(siniestro.motivoRechazo?.takeIf { it.isNotBlank() }, decidido)
                .joinToString(" · ").ifBlank { "No pudimos aprobarlo" },
            AvancePaso.RECHAZADO
        )
    }
    return listOf(primero, segundo, tercero)
}

/**
 * Detalle de un siniestro con su avance (HU05): al tocar una notificación de cambio de estado o de
 * pago paramétrico se abre aquí, ya actualizado. También se llega desde la lista.
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
            Encabezado(
                titulo = siniestro?.let { "Siniestro ${it.siniestroId}" } ?: "Detalle del siniestro",
                onVolver = onVolver
            )

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
    val progreso = progresoDelCaso(siniestro.estado)
    val porcentaje = (progreso * 100).toInt()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp)
            .padding(bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        EtiquetaEstadoSiniestro(siniestro.estado)

        Text(
            text = tituloDelCaso(siniestro),
            style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
            color = MaterialTheme.colorScheme.onSurface
        )
        Text(
            text = "Póliza ${siniestro.polizaId}",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
        )
        // El estado se refresca al abrir; si no se pudo, se avisa sin esconder lo que ya hay.
        if (error != null) {
            Text(
                text = error,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error
            )
        }

        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(
                text = "Progreso del caso",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
            )
            Text(
                text = "$porcentaje%",
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                color = Navegacion
            )
        }
        LinearProgressIndicator(
            progress = { progreso },
            color = Navegacion,
            trackColor = Navegacion.copy(alpha = 0.15f),
            modifier = Modifier
                .fillMaxWidth()
                .semantics { contentDescription = "Progreso del caso, $porcentaje por ciento" }
        )

        Spacer(modifier = Modifier.size(4.dp))
        pasosDelCaso(siniestro).forEach { TarjetaPaso(it) }
    }
}

private fun tituloDelCaso(siniestro: Siniestro): String =
    siniestro.tipoSiniestro?.etiqueta
        ?: if (siniestro.origen == OrigenSiniestro.AUTOMATICO) "Siniestro paramétrico" else "Siniestro reportado"

@Composable
private fun TarjetaPaso(paso: PasoSiniestro) {
    val (icono, color) = when (paso.avance) {
        AvancePaso.HECHO -> Icons.Filled.CheckCircleOutline to Sincronizado
        AvancePaso.EN_CURSO -> Icons.Outlined.Schedule to Navegacion
        AvancePaso.PENDIENTE -> Icons.Outlined.RadioButtonUnchecked to
            MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
        AvancePaso.RECHAZADO -> Icons.Outlined.Cancel to Color(0xFFB00020)
    }
    val estadoTexto = when (paso.avance) {
        AvancePaso.HECHO -> "Completado"
        AvancePaso.EN_CURSO -> "En curso"
        AvancePaso.PENDIENTE -> "Pendiente"
        AvancePaso.RECHAZADO -> "Rechazado"
    }
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f)),
        modifier = Modifier
            .fillMaxWidth()
            .semantics(mergeDescendants = true) { stateDescription = estadoTexto }
    ) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(shape = RoundedCornerShape(12.dp), color = color.copy(alpha = 0.12f)) {
                Icon(
                    imageVector = icono,
                    contentDescription = null,
                    tint = color,
                    modifier = Modifier
                        .padding(10.dp)
                        .size(22.dp)
                )
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    text = paso.titulo,
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                    color = MaterialTheme.colorScheme.onSurface
                )
                Text(
                    text = paso.detalle,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                )
            }
        }
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun ClaimDetailScreenPreview() {
    SolventaTheme {
        ClaimDetailScreen(
            siniestro = Siniestro(
                siniestroId = "ST-2841",
                polizaId = "SV-10482",
                origen = OrigenSiniestro.MANUAL,
                estado = EstadoSiniestro.EN_EVALUACION,
                eventoId = null,
                fechaEvento = "2026-10-18",
                horaEvento = "14:00:00",
                lugar = "Aeropuerto El Dorado",
                descripcion = "Mi equipaje no llegó a destino.",
                estimacionDanos = "800000.00",
                moneda = "COP",
                registradoEn = "2026-10-18T19:35:00Z",
                tipoSiniestro = com.example.solventa.domain.siniestros.TipoSiniestro.INCIDENTE_VIAJE
            ),
            cargando = false,
            error = null,
            onReintentar = {},
            onVolver = {}
        )
    }
}
