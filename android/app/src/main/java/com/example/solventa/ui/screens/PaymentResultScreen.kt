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
import com.example.solventa.R
import com.example.solventa.i18n.Idioma
import com.example.solventa.i18n.tr

/** Confirmación del recaudo (HU13 / HU23): aprobado, rechazado (con reintento) o pendiente. */
@Composable
fun PaymentResultScreen(
    pago: Pago,
    onReintentar: () -> Unit,
    onCerrar: () -> Unit,
    modifier: Modifier = Modifier,
    onInicio: () -> Unit = {},
    onVerBilletera: (() -> Unit)? = null,
    comprobante: ComprobantePago? = null,
    onFirmar: (() -> Unit)? = null
) {
    val verde = Color(0xFF1B8A4A)
    val naranja = Color(0xFFB36B00)
    val rojo = MaterialTheme.colorScheme.error

    val (icono, color, titulo) = when (pago.estado) {
        EstadoPago.APROBADO -> Triple(Icons.Outlined.CheckCircle, verde, tr(R.string.payment_result_pago_exitoso))
        EstadoPago.PENDIENTE -> Triple(Icons.Outlined.Schedule, naranja, tr(R.string.payment_result_pago_pendiente))
        EstadoPago.RECHAZADO -> Triple(Icons.Outlined.Error, rojo, tr(R.string.payment_result_pago_rechazado))
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
                SolventaPrimaryButton(text = tr(R.string.payment_result_reintentar_pago), onClick = onReintentar)
                SolventaSecondaryButton(text = tr(R.string.assistance_cancelar), onClick = onCerrar)
            } else if (pago.estado == EstadoPago.APROBADO && onFirmar != null) {
                SolventaPrimaryButton(text = tr(R.string.payment_result_firmar_contrato), onClick = onFirmar)
                SolventaSecondaryButton(text = tr(R.string.payment_result_cerrar), onClick = onCerrar)
            } else {
                SolventaPrimaryButton(text = tr(R.string.payment_result_cerrar), onClick = onCerrar)
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
                text = tr(R.string.payment_result_comprobante, comprobante.numero),
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
        tr(R.string.payment_result_el_pago_de_se_realizo, formatearMonto(pago.monto, pago.moneda)) +
            tr(R.string.payment_result_para_emitir_tu_poliza_firma)
    EstadoPago.PENDIENTE ->
        tr(R.string.payment_result_tu_pago_esta_pendiente_de)
    EstadoPago.RECHAZADO ->
        tr(R.string.payment_result_tu_pago_fue_rechazado, pago.motivoRechazo?.let { " ($it)" } ?: "") +
            tr(R.string.payment_result_no_se_genero_ninguna_poliza)
}

private fun formatearMonto(valor: BigDecimal, moneda: String): String {
    val formato = NumberFormat.getNumberInstance(Idioma.locale()).apply {
        minimumFractionDigits = if (valor.stripTrailingZeros().scale() > 0) 2 else 0
        maximumFractionDigits = 2
    }
    return "$${formato.format(valor)} $moneda"
}
