package com.example.solventa.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.outlined.AccountBalance
import androidx.compose.material.icons.outlined.CreditCard
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.pagos.EstadoPago
import com.example.solventa.domain.pagos.MetodoPago
import com.example.solventa.domain.pagos.Pago
import com.example.solventa.ui.components.SolventaBottomNavigation
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.theme.Navegacion
import java.math.BigDecimal
import java.text.NumberFormat
import java.util.Locale

/** Historial de pagos del cliente (HU13), equivalente a la pantalla de Pagos en web. */
@Composable
fun PaymentsScreen(
    pagos: List<Pago>,
    cargando: Boolean,
    error: String?,
    onReintentar: () -> Unit,
    onVolver: () -> Unit,
    modifier: Modifier = Modifier,
    onInicio: () -> Unit = {},
    onVerBilletera: (() -> Unit)? = null
) {
    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        bottomBar = { SolventaBottomNavigation(onInicio = onInicio, onPolizas = onVerBilletera) }
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
                    text = "Pagos",
                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                    color = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.weight(1f)
                )
            }
            when {
                pagos.isEmpty() && cargando -> EstadoPagoCentrado {
                    CircularProgressIndicator(color = Navegacion)
                }
                pagos.isEmpty() && error != null -> EstadoPagoCentrado {
                    Text(error, style = MaterialTheme.typography.bodyLarge)
                    Spacer(modifier = Modifier.size(16.dp))
                    SolventaPrimaryButton(text = "Reintentar", onClick = onReintentar)
                }
                pagos.isEmpty() -> EstadoPagoCentrado {
                    Text(
                        text = "Todavía no tienes pagos",
                        style = MaterialTheme.typography.titleMedium
                    )
                    Spacer(modifier = Modifier.size(8.dp))
                    Text(
                        text = "Los pagos de tus primas aparecerán aquí.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                    )
                }
                else -> LazyColumn(
                    contentPadding = PaddingValues(start = 24.dp, end = 24.dp, bottom = 32.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    item {
                        Text(
                            text = "Historial de pagos",
                            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                            modifier = Modifier.padding(top = 12.dp)
                        )
                    }
                    items(pagos, key = { it.pagoId }) { pago -> TarjetaPago(pago) }
                }
            }
        }
    }
}

@Composable
private fun TarjetaPago(pago: Pago) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(shape = RoundedCornerShape(12.dp), color = Navegacion.copy(alpha = 0.1f)) {
                Icon(
                    imageVector = if (pago.metodo == MetodoPago.TARJETA) {
                        Icons.Outlined.CreditCard
                    } else {
                        Icons.Outlined.AccountBalance
                    },
                    contentDescription = null,
                    tint = Navegacion,
                    modifier = Modifier.padding(10.dp).size(22.dp)
                )
            }
            Spacer(modifier = Modifier.size(12.dp))
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = "Prima — cotización ${pago.cotizacionId}",
                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                    color = MaterialTheme.colorScheme.onSurface
                )
                Text(
                    text = "${etiquetaMetodo(pago.metodo)} · ${formatearMontoPago(pago.monto, pago.moneda)}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            }
            EtiquetaEstadoPago(pago.estado)
        }
    }
}

@Composable
private fun EtiquetaEstadoPago(estado: EstadoPago) {
    val (color, texto) = when (estado) {
        EstadoPago.APROBADO -> Color(0xFF1B8A4A) to "Pagado"
        EstadoPago.PENDIENTE -> Color(0xFFB36B00) to "Pendiente"
        EstadoPago.RECHAZADO -> Color(0xFFC0392B) to "Rechazado"
    }
    Surface(shape = RoundedCornerShape(8.dp), color = color.copy(alpha = 0.15f)) {
        Text(
            text = texto,
            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
            color = color,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
        )
    }
}

@Composable
private fun EstadoPagoCentrado(contenido: @Composable () -> Unit) {
    Box(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) { contenido() }
    }
}

private fun etiquetaMetodo(metodo: MetodoPago): String = when (metodo) {
    MetodoPago.TARJETA -> "Tarjeta"
    MetodoPago.PSE -> "PSE"
}

private fun formatearMontoPago(valor: BigDecimal, moneda: String): String {
    val formato = NumberFormat.getNumberInstance(Locale.forLanguageTag("es-CO")).apply {
        minimumFractionDigits = if (valor.stripTrailingZeros().scale() > 0) 2 else 0
        maximumFractionDigits = 2
    }
    return "$${formato.format(valor)} $moneda"
}
