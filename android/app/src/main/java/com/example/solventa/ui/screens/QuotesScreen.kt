package com.example.solventa.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.example.solventa.domain.cotizaciones.ResultadoCotizacion
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SeccionNavegacion
import com.example.solventa.ui.components.SolventaBottomNavigation
import com.example.solventa.ui.cotizaciones.CotizacionDemostracion
import com.example.solventa.ui.theme.Atencion
import com.example.solventa.ui.theme.Avance
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.SolventaTheme
import java.text.NumberFormat
import com.example.solventa.R
import com.example.solventa.i18n.Idioma
import com.example.solventa.i18n.tr

@Composable
fun QuotesScreen(
    cotizaciones: List<ResultadoCotizacion>,
    cargando: Boolean,
    error: String?,
    onVerCotizacion: (String) -> Unit,
    onReintentar: () -> Unit,
    onVolver: () -> Unit,
    modifier: Modifier = Modifier,
    onCrearCotizacion: () -> Unit = {},
    onInicio: () -> Unit = {},
    onPolizas: (() -> Unit)? = null,
    onSiniestros: (() -> Unit)? = null,
    onPagos: (() -> Unit)? = null
) {
    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        bottomBar = {
            SolventaBottomNavigation(
                onInicio = onInicio,
                onPolizas = onPolizas,
                onSiniestros = onSiniestros,
                onPagos = onPagos,
                seleccionada = SeccionNavegacion.COTIZACIONES
            )
        }
    ) { paddingValues ->
        Column(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
            Encabezado(titulo = tr(R.string.quotes_cotizaciones), onVolver = onVolver)
            when {
                cotizaciones.isEmpty() && cargando -> EstadoCentrado {
                    CircularProgressIndicator(
                        color = Navegacion,
                        modifier = Modifier.semantics {
                            contentDescription = tr(R.string.quotes_cargando_tus_cotizaciones)
                        }
                    )
                }
                cotizaciones.isEmpty() && error != null -> EstadoCentrado {
                    Text(error, style = MaterialTheme.typography.bodyLarge)
                    Spacer(modifier = Modifier.size(16.dp))
                    SolventaPrimaryButton(text = tr(R.string.assistance_reintentar), onClick = onReintentar)
                }
                cotizaciones.isEmpty() -> EstadoCentrado {
                    Text(
                        text = tr(R.string.quotes_aun_no_tienes_cotizaciones),
                        style = MaterialTheme.typography.titleMedium
                    )
                    Spacer(modifier = Modifier.size(8.dp))
                    Text(
                        text = tr(R.string.quotes_las_cotizaciones_que_calcules_apareceran),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                    )
                    Spacer(modifier = Modifier.size(20.dp))
                    SolventaPrimaryButton(text = tr(R.string.quotes_crear_cotizacion), onClick = onCrearCotizacion)
                }
                else -> ListaCotizaciones(cotizaciones, error, onVerCotizacion, onCrearCotizacion)
            }
        }
    }
}

@Composable
private fun ListaCotizaciones(
    cotizaciones: List<ResultadoCotizacion>,
    error: String?,
    onVerCotizacion: (String) -> Unit,
    onCrearCotizacion: () -> Unit
) {
    LazyColumn(
        contentPadding = PaddingValues(start = 24.dp, end = 24.dp, bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Column(modifier = Modifier.padding(top = 12.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                SolventaPrimaryButton(text = tr(R.string.quotes_crear_cotizacion), onClick = onCrearCotizacion)
                Text(
                    text = tr(R.string.quotes_cotizaciones_recientes),
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                )
            }
        }
        if (error != null) {
            item { Text(error, style = MaterialTheme.typography.bodyMedium, color = Atencion) }
        }
        items(cotizaciones, key = { it.cotizacionId }) { cotizacion ->
            TarjetaCotizacion(cotizacion) { onVerCotizacion(cotizacion.cotizacionId) }
        }
    }
}

@Composable
private fun TarjetaCotizacion(cotizacion: ResultadoCotizacion, onClick: () -> Unit) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f)),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(role = Role.Button, onClickLabel = tr(R.string.quotes_ver_cotizacion), onClick = onClick)
    ) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = nombreRamo(cotizacion.ramo),
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.weight(1f, fill = false)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    EtiquetaCotizacion(cotizacion.estado)
                }
                Text(
                    text = moneda(cotizacion),
                    style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold),
                    color = Navegacion
                )
                Text(
                    text = cotizacion.coberturaPrincipal.nombre,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
                Text(
                    text = tr(R.string.quotes_referencia, cotizacion.cotizacionId),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f)
                )
            }
            Icon(
                imageVector = Icons.Filled.ChevronRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)
            )
        }
    }
}

@Composable
private fun EtiquetaCotizacion(estado: String) {
    val vigente = estado == "VIGENTE"
    Surface(
        shape = RoundedCornerShape(8.dp),
        color = if (vigente) Avance.copy(alpha = 0.25f) else Color.Gray.copy(alpha = 0.15f)
    ) {
        Text(
            text = estado.lowercase().replaceFirstChar { it.titlecase() },
            style = MaterialTheme.typography.labelMedium,
            color = if (vigente) Color(0xFF2F5A0B) else MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
        )
    }
}

@Composable
private fun EstadoCentrado(contenido: @Composable () -> Unit) {
    Box(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) { contenido() }
    }
}

private fun nombreRamo(ramo: RamoCotizacion): String = when (ramo) {
    RamoCotizacion.VIAJE -> tr(R.string.quote_form_seguro_de_viaje)
    RamoCotizacion.DISPOSITIVOS -> tr(R.string.quote_form_proteccion_de_dispositivos)
    RamoCotizacion.VIDA -> tr(R.string.quote_form_seguro_de_vida)
    RamoCotizacion.PARAMETRICO -> tr(R.string.quote_form_seguro_parametrico)
}

private fun moneda(cotizacion: ResultadoCotizacion): String {
    val formato = NumberFormat.getCurrencyInstance(Idioma.locale()).apply {
        maximumFractionDigits = 0
    }
    return "${formato.format(cotizacion.primaTotal)} ${cotizacion.moneda}"
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
private fun QuotesScreenPreview() {
    SolventaTheme {
        QuotesScreen(
            cotizaciones = listOf(CotizacionDemostracion.para(RamoCotizacion.VIAJE)),
            cargando = false,
            error = null,
            onVerCotizacion = {},
            onReintentar = {},
            onVolver = {}
        )
    }
}
