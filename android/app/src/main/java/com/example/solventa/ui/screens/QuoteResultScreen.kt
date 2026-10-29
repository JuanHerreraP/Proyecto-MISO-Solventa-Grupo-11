package com.example.solventa.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.outlined.Check
import androidx.compose.material.icons.outlined.Shield
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
import androidx.compose.ui.graphics.vector.rememberVectorPainter
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.cotizaciones.CatalogoCotizaciones
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.example.solventa.domain.cotizaciones.ResultadoCotizacion
import com.example.solventa.ui.components.SolventaBottomNavigation
import com.example.solventa.ui.components.SolventaNoticePill
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaSecondaryButton
import com.example.solventa.ui.cotizaciones.CotizacionDemostracion
import com.example.solventa.ui.theme.Avance
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.Noche
import com.example.solventa.ui.theme.SolventaTheme
import java.math.BigDecimal
import java.text.NumberFormat
import java.util.Locale

/** Presenta el precio y la cobertura calculados sin conocer el origen de los datos. */
@Composable
fun QuoteResultScreen(
    cotizacion: ResultadoCotizacion,
    onVolver: () -> Unit,
    onAceptar: () -> Unit,
    onCrearOtra: () -> Unit,
    modifier: Modifier = Modifier,
    onInicio: () -> Unit = {},
    onVerBilletera: (() -> Unit)? = null,
    modoDetalle: Boolean = false
) {
    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        bottomBar = {
            SolventaBottomNavigation(onInicio = onInicio, onPolizas = onVerBilletera)
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
        ) {
            EncabezadoResultado(onVolver = onVolver)
            Column(
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 18.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Text(
                    text = "COTIZACIÓN",
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                    color = Navegacion
                )
                Text(
                    text = tituloResultado(cotizacion.ramo),
                    style = MaterialTheme.typography.headlineMedium,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Text(
                    text = "Cotización vigente durante las próximas 24 horas.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
                )

                TarjetaPrima(cotizacion)
                TarjetaCobertura(cotizacion)
                if (cotizacion.datosRiesgo.keys.any { it != "valor_asegurado" }) {
                    TarjetaDatosSolicitud(cotizacion)
                }

                if (cotizacion.perfilRiesgoId != null) {
                    SolventaNoticePill(
                        text = "Precio personalizado con la información que autorizaste.",
                        icon = rememberVectorPainter(Icons.Outlined.Shield),
                        containerColor = Avance.copy(alpha = 0.16f),
                        contentColor = Color(0xFF47720D)
                    )
                }

                if (modoDetalle) {
                    SolventaPrimaryButton(text = "Cerrar", onClick = onVolver)
                } else {
                    SolventaPrimaryButton(
                        text = "Aceptar y continuar",
                        onClick = onAceptar,
                        enabled = cotizacion.estado == "VIGENTE"
                    )
                    SolventaSecondaryButton(text = "Crear otra cotización", onClick = onCrearOtra)
                }
            }
        }
    }
}

@Composable
private fun EncabezadoResultado(onVolver: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp, vertical = 8.dp),
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
            text = "Tu cotización",
            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
            color = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.weight(1f)
        )
        Text(
            text = "PASO 3 DE 3",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f),
            modifier = Modifier.padding(end = 12.dp)
        )
    }
}

@Composable
private fun TarjetaPrima(cotizacion: ResultadoCotizacion) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = Noche,
        shape = RoundedCornerShape(18.dp)
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "PRIMA TOTAL",
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                    color = Color.White.copy(alpha = 0.7f)
                )
                Spacer(modifier = Modifier.weight(1f))
                Surface(color = Avance, shape = RoundedCornerShape(50)) {
                    Text(
                        text = etiquetaEstado(cotizacion.estado),
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                        color = Noche,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp)
                    )
                }
            }
            Text(
                text = formatearMoneda(cotizacion.primaTotal, cotizacion.moneda),
                style = MaterialTheme.typography.headlineLarge,
                color = Color.White
            )
        }
    }
}

@Composable
private fun TarjetaCobertura(cotizacion: ResultadoCotizacion) {
    val cobertura = cotizacion.coberturaPrincipal
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.surface,
        shape = RoundedCornerShape(18.dp),
        border = androidx.compose.foundation.BorderStroke(
            1.dp,
            MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f)
        )
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = "Cobertura principal",
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.onSurface
            )
            DatoCobertura(cobertura.nombre)
            DatoCobertura(
                "Suma asegurada: ${formatearMoneda(cobertura.sumaAsegurada, cotizacion.moneda)}"
            )
            cobertura.descripcion?.takeIf(String::isNotBlank)?.let { DatoCobertura(it) }
        }
    }
}

@Composable
private fun TarjetaDatosSolicitud(cotizacion: ResultadoCotizacion) {
    val etiquetas = CatalogoCotizaciones.definicion(cotizacion.ramo)
        .campos.associate { it.codigo to it.etiqueta }
    // La suma/valor asegurado ya se muestra en la tarjeta de cobertura.
    val datos = cotizacion.datosRiesgo.filterKeys { it != "valor_asegurado" }
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.surface,
        shape = RoundedCornerShape(18.dp),
        border = androidx.compose.foundation.BorderStroke(
            1.dp,
            MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f)
        )
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = "Datos de la solicitud",
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.onSurface
            )
            datos.forEach { (codigo, valor) ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text(
                        text = etiquetas[codigo] ?: codigo,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                        modifier = Modifier.weight(1f)
                    )
                    Text(
                        text = valor,
                        style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }
        }
    }
}

@Composable
private fun DatoCobertura(texto: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.Top
    ) {
        Icon(
            imageVector = Icons.Outlined.Check,
            contentDescription = null,
            tint = Color(0xFF2F8F64),
            modifier = Modifier.size(18.dp)
        )
        Text(
            text = texto,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.78f),
            modifier = Modifier.weight(1f)
        )
    }
}

private fun tituloResultado(ramo: RamoCotizacion): String = when (ramo) {
    RamoCotizacion.VIAJE -> "Protección para tu viaje"
    RamoCotizacion.DISPOSITIVOS -> "Protección para tu dispositivo"
    RamoCotizacion.VIDA -> "Protección para tu vida"
    RamoCotizacion.PARAMETRICO -> "Protección ante eventos"
}

private fun etiquetaEstado(estado: String): String = when (estado) {
    "VIGENTE" -> "VIGENTE 24 H"
    else -> estado.replace('_', ' ')
}

private fun formatearMoneda(valor: BigDecimal, moneda: String): String {
    val formato = NumberFormat.getNumberInstance(Locale.forLanguageTag("es-CO")).apply {
        minimumFractionDigits = if (valor.stripTrailingZeros().scale() > 0) 2 else 0
        maximumFractionDigits = 2
    }
    return "$${formato.format(valor)} $moneda"
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
private fun QuoteResultScreenPreview() {
    SolventaTheme {
        QuoteResultScreen(
            cotizacion = CotizacionDemostracion.para(RamoCotizacion.VIAJE),
            onVolver = {},
            onAceptar = {},
            onCrearOtra = {}
        )
    }
}

