package com.example.solventa.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Error
import androidx.compose.material.icons.outlined.Schedule
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.pagos.ComprobantePago
import com.example.solventa.domain.pagos.EstadoPago
import com.example.solventa.domain.pagos.Pago
import com.example.solventa.ui.components.SolventaBottomNavigation
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaSecondaryButton
import java.math.BigDecimal
import java.text.NumberFormat
import java.util.Locale

/** Confirmación del recaudo (HU13 / HU23): aprobado, rechazado (con reintento) o pendiente. */
@Composable
fun PaymentResultScreen(
    pago: Pago,
    onReintentar: () -> Unit,
    onCerrar: () -> Unit,
    modifier: Modifier = Modifier,
    onInicio: () -> Unit = {},
    onVerBilletera: (() -> Unit)? = null,
    comprobante: ComprobantePago? = null
) {
    val verde = Color(0xFF1B8A4A)
    val naranja = Color(0xFFB36B00)
    val rojo = MaterialTheme.colorScheme.error

    val (icono, color, titulo) = when (pago.estado) {
        EstadoPago.APROBADO -> Triple(Icons.Outlined.CheckCircle, verde, "¡Pago exitoso!")
        EstadoPago.PENDIENTE -> Triple(Icons.Outlined.Schedule, naranja, "Pago pendiente")
        EstadoPago.RECHAZADO -> Triple(Icons.Outlined.Error, rojo, "Pago rechazado")
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        bottomBar = { SolventaBottomNavigation(onInicio = onInicio, onPolizas = onVerBilletera) }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(horizontal = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            IconoEstado(icono, color)
            Text(
                text = titulo,
                style = MaterialTheme.typography.headlineMedium,
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.padding(top = 20.dp)
            )
            Text(
                text = mensajeResultado(pago),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 10.dp, bottom = 28.dp)
            )
            if (pago.estado == EstadoPago.APROBADO && comprobante != null) {
                ResumenComprobante(comprobante)
            }

            if (pago.estado == EstadoPago.RECHAZADO) {
                SolventaPrimaryButton(text = "Reintentar pago", onClick = onReintentar)
                SolventaSecondaryButton(text = "Cancelar", onClick = onCerrar)
            } else {
                SolventaPrimaryButton(text = "Cerrar", onClick = onCerrar)
            }
        }
    }
}

@Composable
private fun IconoEstado(icono: ImageVector, color: Color) {
    Surface(color = color.copy(alpha = 0.12f), shape = CircleShape) {
        Icon(
            imageVector = icono,
            contentDescription = null,
            tint = color,
            modifier = Modifier
                .padding(18.dp)
                .size(48.dp)
        )
    }
}

/** El comprobante del pago aprobado (HU21): número, concepto y valor. */
@Composable
private fun ResumenComprobante(comprobante: ComprobantePago) {
    Surface(
        shape = androidx.compose.foundation.shape.RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 24.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                text = "Comprobante ${comprobante.numero}",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = comprobante.descripcion,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
            Text(
                text = formatearMonto(comprobante.monto, comprobante.moneda),
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}

private fun mensajeResultado(pago: Pago): String = when (pago.estado) {
    EstadoPago.APROBADO ->
        "El pago de ${formatearMonto(pago.monto, pago.moneda)} se realizó de forma satisfactoria. " +
            "Para emitir tu póliza, firma tu contrato en el portal web."
    EstadoPago.PENDIENTE ->
        "Tu pago está pendiente de confirmación con tu banco."
    EstadoPago.RECHAZADO ->
        "Tu pago fue rechazado${pago.motivoRechazo?.let { " ($it)" } ?: ""}. " +
            "No se generó ninguna póliza. Puedes intentarlo de nuevo."
}

private fun formatearMonto(valor: BigDecimal, moneda: String): String {
    val formato = NumberFormat.getNumberInstance(Locale.forLanguageTag("es-CO")).apply {
        minimumFractionDigits = if (valor.stripTrailingZeros().scale() > 0) 2 else 0
        maximumFractionDigits = 2
    }
    return "$${formato.format(valor)} $moneda"
}
