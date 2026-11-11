package com.example.solventa.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.rememberVectorPainter
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.polizas.BloqueoRenovacion
import com.example.solventa.domain.polizas.CoberturaRenovacion
import com.example.solventa.domain.polizas.Formatos
import com.example.solventa.domain.polizas.PropuestaRenovacion
import com.example.solventa.domain.polizas.VigenciaRenovacion
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaSecondaryButton
import com.example.solventa.ui.theme.Atencion
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.SolventaTheme

/** Renovación de una póliza: nueva vigencia, coberturas y prima recalculada (HU22 / BPM-35). */
@Composable
fun RenewalScreen(
    propuesta: PropuestaRenovacion?,
    cargando: Boolean,
    error: String?,
    iniciando: Boolean,
    onConfirmar: () -> Unit,
    onReintentar: () -> Unit,
    onAhoraNo: () -> Unit,
    onVolver: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
        Column(modifier = Modifier.fillMaxSize()) {
            Encabezado(titulo = "Pólizas", onVolver = onVolver)

            when {
                propuesta == null && cargando -> Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(
                        color = Navegacion,
                        modifier = Modifier.semantics {
                            contentDescription = "Cargando las condiciones de la renovación"
                        }
                    )
                }

                propuesta == null -> Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = error ?: "No pudimos cargar la renovación.",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.size(16.dp))
                    SolventaPrimaryButton(text = "Reintentar", onClick = onReintentar)
                }

                else -> Contenido(
                    propuesta = propuesta,
                    error = error,
                    iniciando = iniciando,
                    onConfirmar = onConfirmar,
                    onAhoraNo = onAhoraNo
                )
            }
        }
    }
}

@Composable
private fun Contenido(
    propuesta: PropuestaRenovacion,
    error: String?,
    iniciando: Boolean,
    onConfirmar: () -> Unit,
    onAhoraNo: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp)
            .padding(bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(
                text = "Continúa protegido",
                style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = "Revisa las condiciones de la nueva vigencia.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
        }

        val vigencia = propuesta.nuevaVigencia
        if (propuesta.renovable && vigencia != null) {
            Surface(
                shape = RoundedCornerShape(16.dp),
                color = MaterialTheme.colorScheme.surface,
                border = BorderStroke(1.dp, BordeRenovacion),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Titulo("Nueva vigencia")
                    Detalle(Formatos.vigencia(vigencia.inicio, vigencia.fin))
                    Spacer(modifier = Modifier.size(2.dp))
                    Titulo("Coberturas")
                    Detalle(propuesta.coberturas.joinToString(", ") { it.nombre })
                }
            }

            propuesta.primaNueva?.let { prima ->
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Text(
                            text = "Prima de renovación",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                        )
                        Text(
                            text = "${Formatos.dinero(prima, propuesta.moneda)} ${propuesta.moneda}",
                            style = MaterialTheme.typography.headlineSmall.copy(
                                fontWeight = FontWeight.Bold
                            ),
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                }
            }
        } else {
            // No se puede renovar: se explica el motivo y solo queda "Ahora no".
            Surface(
                shape = RoundedCornerShape(16.dp),
                color = Atencion.copy(alpha = 0.14f),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Titulo("Esta póliza no se puede renovar todavía")
                    propuesta.bloqueos.ifEmpty {
                        listOf(BloqueoRenovacion("", "No se puede renovar en este momento."))
                    }.forEach { Detalle(it.mensaje) }
                }
            }
        }

        if (error != null) {
            Text(
                text = error,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error
            )
        }

        if (propuesta.renovable) {
            SolventaPrimaryButton(
                text = "Confirmar y pagar",
                onClick = onConfirmar,
                isLoading = iniciando
            )
        }
        SolventaSecondaryButton(
            text = "Ahora no",
            onClick = onAhoraNo,
            enabled = !iniciando,
            icon = rememberVectorPainter(Icons.AutoMirrored.Filled.ArrowForward),
            contentColor = MaterialTheme.colorScheme.onSurface
        )
    }
}

private val BordeRenovacion = Color(0xFFE2E8F0)

@Composable
private fun Titulo(texto: String) {
    Text(
        text = texto,
        style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
        color = MaterialTheme.colorScheme.onSurface
    )
}

@Composable
private fun Detalle(texto: String) {
    Text(
        text = texto,
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
    )
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun RenewalScreenPreview() {
    SolventaTheme {
        RenewalScreen(
            propuesta = PropuestaRenovacion(
                polizaId = "1",
                renovable = true,
                bloqueos = emptyList(),
                nuevaVigencia = VigenciaRenovacion("2026-10-21", "2027-10-21"),
                coberturas = listOf(CoberturaRenovacion("Asistencia médica, cancelación y equipaje", true)),
                primaNueva = "164700.00",
                moneda = "COP",
                renovacion = null
            ),
            cargando = false,
            error = null,
            iniciando = false,
            onConfirmar = {},
            onReintentar = {},
            onAhoraNo = {},
            onVolver = {}
        )
    }
}
