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
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.pagos.ComprobantePago
import com.example.solventa.domain.pagos.ConceptoPago
import com.example.solventa.domain.pagos.EstadoPago
import com.example.solventa.domain.pagos.MetodoPago
import com.example.solventa.domain.pagos.Pago
import com.example.solventa.domain.pagos.PrimaPendiente
import com.example.solventa.domain.pagos.TipoPrimaPendiente
import com.example.solventa.domain.polizas.Formatos
import com.example.solventa.ui.components.SolventaBottomNavigation
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.theme.Atencion
import com.example.solventa.ui.theme.Navegacion
import java.math.BigDecimal
import java.text.NumberFormat
import java.util.Locale

/**
 * Pagos del cliente: lo que tiene pendiente de pagar o firmar (HU21) y el historial de pagos
 * con su comprobante (HU13 / HU21). Equivalente a la pantalla de Pagos en web.
 */
@Composable
fun PaymentsScreen(
    pagos: List<Pago>,
    cargando: Boolean,
    error: String?,
    onReintentar: () -> Unit,
    onVolver: () -> Unit,
    modifier: Modifier = Modifier,
    onInicio: () -> Unit = {},
    onVerBilletera: (() -> Unit)? = null,
    pendientes: List<PrimaPendiente> = emptyList(),
    errorPendientes: String? = null,
    onPagar: (PrimaPendiente) -> Unit = {},
    onVerComprobante: (Pago) -> Unit = {},
    comprobanteVisible: Boolean = false,
    comprobante: ComprobantePago? = null,
    errorComprobante: String? = null,
    onCerrarComprobante: () -> Unit = {}
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
            val sinNada = pagos.isEmpty() && pendientes.isEmpty()
            when {
                sinNada && cargando -> EstadoPagoCentrado {
                    CircularProgressIndicator(color = Navegacion)
                }
                sinNada && error != null -> EstadoPagoCentrado {
                    Text(error, style = MaterialTheme.typography.bodyLarge)
                    Spacer(modifier = Modifier.size(16.dp))
                    SolventaPrimaryButton(text = "Reintentar", onClick = onReintentar)
                }
                sinNada -> EstadoPagoCentrado {
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
                    if (errorPendientes != null) {
                        item {
                            Text(
                                text = errorPendientes,
                                style = MaterialTheme.typography.bodyMedium,
                                color = Atencion,
                                modifier = Modifier.padding(top = 12.dp)
                            )
                        }
                    }
                    if (pendientes.isNotEmpty()) {
                        item { TituloSeccion("Pendientes de pago") }
                        items(pendientes, key = { "${it.tipo}-${it.referenciaId}" }) { prima ->
                            TarjetaPendiente(prima, onPagar)
                        }
                    }
                    if (pagos.isNotEmpty()) {
                        item { TituloSeccion("Historial de pagos") }
                        items(pagos, key = { it.pagoId }) { pago ->
                            TarjetaPago(pago, onVerComprobante)
                        }
                    }
                }
            }
        }
    }

    if (comprobanteVisible) {
        DialogoComprobante(
            comprobante = comprobante,
            error = errorComprobante,
            onCerrar = onCerrarComprobante
        )
    }
}

@Composable
private fun TituloSeccion(texto: String) {
    Text(
        text = texto,
        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
        modifier = Modifier.padding(top = 12.dp)
    )
}

@Composable
private fun TarjetaPendiente(prima: PrimaPendiente, onPagar: (PrimaPendiente) -> Unit) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(
                text = descripcionPendiente(prima),
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
            if (prima.sePaga) {
                Text(
                    text = formatearMontoPago(prima.monto, prima.moneda),
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface
                )
                prima.fechaLimite?.let {
                    Text(
                        text = "Fecha límite: ${Formatos.fechaHora(it)}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                    )
                }
                Spacer(modifier = Modifier.size(4.dp))
                SolventaPrimaryButton(text = "Pagar", onClick = { onPagar(prima) }, height = 44.dp)
            } else {
                // La firma del contrato aún no está en la app: se hace en el portal web.
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Outlined.Info,
                        contentDescription = null,
                        tint = Atencion,
                        modifier = Modifier.size(20.dp)
                    )
                    Text(
                        text = prima.mensaje ?: "Firma tu contrato en el portal web para emitir tu póliza.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f)
                    )
                }
            }
        }
    }
}

private fun descripcionPendiente(prima: PrimaPendiente): String = when (prima.tipo) {
    TipoPrimaPendiente.RENOVACION -> "Renovación — póliza ${prima.numeroPoliza ?: prima.polizaId.orEmpty()}"
    TipoPrimaPendiente.COTIZACION -> "${prima.nombreRamo} — cotización ${prima.cotizacionId}"
    TipoPrimaPendiente.FIRMA_PENDIENTE -> "${prima.nombreRamo} — contrato por firmar"
}

@Composable
private fun TarjetaPago(pago: Pago, onVerComprobante: (Pago) -> Unit) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
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
                    val concepto = if (pago.concepto == ConceptoPago.RENOVACION) "Renovación" else "Prima"
                    Text(
                        text = "$concepto — cotización ${pago.cotizacionId}",
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
            if (pago.estado == EstadoPago.APROBADO) {
                TextButton(onClick = { onVerComprobante(pago) }) {
                    Text("Ver comprobante", color = Navegacion)
                }
            }
        }
    }
}

@Composable
private fun DialogoComprobante(
    comprobante: ComprobantePago?,
    error: String?,
    onCerrar: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onCerrar,
        title = { Text("Comprobante de pago") },
        text = {
            when {
                comprobante != null -> Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    DatoComprobante("Comprobante", comprobante.numero)
                    DatoComprobante("Concepto", comprobante.descripcion)
                    DatoComprobante("Valor pagado", formatearMontoPago(comprobante.monto, comprobante.moneda))
                    DatoComprobante("Medio de pago", etiquetaMetodo(comprobante.metodo))
                    DatoComprobante("Fecha de pago", Formatos.fechaHora(comprobante.pagadoEn))
                    comprobante.referenciaPasarela?.let { DatoComprobante("Referencia", it) }
                }
                error != null -> Text(error, color = MaterialTheme.colorScheme.error)
                // Sin comprobante ni error todavía: se está consultando.
                else -> CircularProgressIndicator(
                    color = Navegacion,
                    modifier = Modifier.semantics { contentDescription = "Cargando el comprobante" }
                )
            }
        },
        confirmButton = { TextButton(onClick = onCerrar) { Text("Cerrar") } }
    )
}

@Composable
private fun DatoComprobante(etiqueta: String, valor: String) {
    Column {
        Text(
            text = etiqueta,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
        )
        Text(
            text = valor,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface
        )
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
