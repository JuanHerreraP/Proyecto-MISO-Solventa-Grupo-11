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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
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
import com.example.solventa.domain.polizas.CategoriaMovimiento
import com.example.solventa.domain.polizas.Formatos
import com.example.solventa.domain.polizas.HistorialPoliza
import com.example.solventa.domain.polizas.MovimientoPoliza
import com.example.solventa.domain.polizas.NaturalezaMonto
import com.example.solventa.domain.polizas.TipoMovimiento
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.SolventaTheme

/**
 * Historial detallado de movimientos de una póliza contratada (HU25).
 * Se accede desde el detalle de la póliza con el botón "Ver historial de movimientos".
 * Consume el endpoint consolidado /historial: emisión, pago de prima inicial, endosos y desembolsos.
 */
@Composable
fun PolicyHistoryScreen(
    numeroPoliza: String,
    nombreRamo: String,
    historial: HistorialPoliza?,
    cargando: Boolean,
    error: String?,
    onReintentar: () -> Unit,
    onVolver: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
        Column(modifier = Modifier.fillMaxSize()) {
            Encabezado(titulo = "Historial de la póliza", onVolver = onVolver)

            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 24.dp)
                    .padding(bottom = 32.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        text = nombreRamo,
                        style = MaterialTheme.typography.headlineSmall,
                        color = MaterialTheme.colorScheme.onBackground
                    )
                    if (numeroPoliza.isNotBlank()) {
                        Text(
                            text = "Póliza $numeroPoliza",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                        )
                    }
                }

                when {
                    historial == null && cargando -> Box(
                        modifier = Modifier.fillMaxWidth().padding(top = 48.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator(
                            color = Navegacion,
                            modifier = Modifier.semantics {
                                contentDescription = "Cargando movimientos"
                            }
                        )
                    }

                    historial == null && error != null -> Column(
                        modifier = Modifier.fillMaxWidth().padding(top = 32.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        Text(
                            text = error,
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.error
                        )
                        SolventaPrimaryButton(text = "Reintentar", onClick = onReintentar)
                    }

                    historial?.movimientos.isNullOrEmpty() -> Text(
                        text = "Esta póliza no tiene movimientos registrados.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                    )

                    else -> Surface(
                        shape = RoundedCornerShape(16.dp),
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            historial?.movimientos.orEmpty().forEachIndexed { indice, movimiento ->
                                if (indice > 0) HorizontalDivider()
                                Movimiento(movimiento)
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.size(0.dp))
            }
        }
    }
}

@Composable
private fun Movimiento(movimiento: MovimientoPoliza) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top
        ) {
            Text(
                text = movimiento.tipo.titulo(),
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
            if (movimiento.estado != null) {
                ChipEstado(movimiento.estado)
            }
        }
        Text(
            text = Formatos.fechaHora(movimiento.fecha),
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
        )
        Text(
            text = movimiento.descripcion,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface
        )
        if (movimiento.monto != null) {
            Text(
                text = montoConSigno(movimiento.monto, movimiento.moneda, movimiento.naturalezaMonto),
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold),
                color = MaterialTheme.colorScheme.onSurface
            )
        }
        movimiento.cambios.forEach { cambio ->
            Text(
                text = cambio.descripcion,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f)
            )
        }
    }
}

@Composable
private fun ChipEstado(estado: String) {
    Surface(
        shape = RoundedCornerShape(50),
        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f)
    ) {
        Text(
            text = estado,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f),
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
        )
    }
}

/** Título legible por tipo de movimiento, igual que la web (HU25). */
private fun TipoMovimiento.titulo(): String = when (this) {
    TipoMovimiento.EMISION -> "Emisión de póliza"
    TipoMovimiento.PAGO_PRIMA_INICIAL -> "Pago de prima inicial"
    TipoMovimiento.ENDOSO -> "Modificación contractual"
    TipoMovimiento.RENOVACION -> "Renovación"
    TipoMovimiento.CANCELACION -> "Cancelación"
    TipoMovimiento.DESEMBOLSO_INDEMNIZACION -> "Pago de indemnización"
    TipoMovimiento.REEMBOLSO -> "Reembolso"
}

/**
 * El monto siempre llega positivo; el signo mostrado depende de la naturaleza:
 * COBRO antepone "−", REEMBOLSO/INDEMNIZACION anteponen "+", el resto va sin signo.
 */
private fun montoConSigno(monto: String, moneda: String?, naturaleza: NaturalezaMonto?): String {
    val formateado = Formatos.dinero(monto, moneda ?: "COP")
    return when (naturaleza) {
        NaturalezaMonto.COBRO -> "−$formateado"
        NaturalezaMonto.REEMBOLSO, NaturalezaMonto.INDEMNIZACION -> "+$formateado"
        else -> formateado
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun PolicyHistoryScreenPreview() {
    SolventaTheme {
        PolicyHistoryScreen(
            numeroPoliza = "SOL-VJ-0001",
            nombreRamo = "Seguro de viaje",
            historial = HistorialPoliza(
                polizaId = "POL-1",
                numeroPoliza = "SOL-VJ-0001",
                nombreRamo = "Seguro de viaje",
                estado = "VIGENTE",
                movimientos = listOf(
                    MovimientoPoliza(
                        movimientoId = "m1",
                        polizaId = "POL-1",
                        categoria = CategoriaMovimiento.POLIZA,
                        tipo = TipoMovimiento.EMISION,
                        fecha = "2026-10-01T10:00:00Z",
                        descripcion = "Se emitió la póliza con las coberturas contratadas.",
                        referencia = null,
                        referenciaExterna = null,
                        estado = "EMITIDA",
                        monto = null,
                        moneda = null,
                        naturalezaMonto = null,
                        cambios = emptyList()
                    ),
                    MovimientoPoliza(
                        movimientoId = "m2",
                        polizaId = "POL-1",
                        categoria = CategoriaMovimiento.FINANCIERO,
                        tipo = TipoMovimiento.PAGO_PRIMA_INICIAL,
                        fecha = "2026-10-01T10:05:00Z",
                        descripcion = "Pago de la prima inicial.",
                        referencia = "PAGO-123",
                        referenciaExterna = "PSE-999",
                        estado = "CONFIRMADO",
                        monto = "84000.00",
                        moneda = "COP",
                        naturalezaMonto = NaturalezaMonto.COBRO,
                        cambios = emptyList()
                    )
                )
            ),
            cargando = false,
            error = null,
            onReintentar = {},
            onVolver = {}
        )
    }
}
