package com.example.solventa.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.outlined.CloudDone
import androidx.compose.material.icons.outlined.CloudOff
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.polizas.Billetera
import com.example.solventa.domain.polizas.EstadoPoliza
import com.example.solventa.domain.polizas.Formatos
import com.example.solventa.domain.polizas.PolizaResumen
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.theme.Atencion
import com.example.solventa.ui.theme.Avance
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.Offline
import com.example.solventa.ui.theme.Sincronizado
import com.example.solventa.ui.theme.SolventaTheme

/** Billetera digital de pólizas (HU07 / BPM-31). Solo se compone con una sesión activa. */
@Composable
fun WalletScreen(
    billetera: Billetera?,
    cargando: Boolean,
    error: String?,
    sinConexion: Boolean = false,
    ultimaSincronizacionMs: Long? = null,
    datosAntiguos: Boolean = false,
    falloSincronizacionPersistente: Boolean = false,
    onVerPoliza: (String) -> Unit,
    onReintentar: () -> Unit,
    onVolver: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
        Column(modifier = Modifier.fillMaxSize()) {
            Encabezado(
                titulo = "Pólizas",
                onVolver = onVolver,
                accion = { IndicadorConexion(sinConexion = sinConexion) }
            )
            EstadoSincronizacion(
                sinConexion = sinConexion,
                ultimaSincronizacionMs = ultimaSincronizacionMs,
                datosAntiguos = datosAntiguos,
                falloPersistente = falloSincronizacionPersistente
            )

            when {
                billetera == null && cargando -> Centrado {
                    CircularProgressIndicator(
                        color = Navegacion,
                        modifier = Modifier.semantics { contentDescription = "Cargando tus pólizas" }
                    )
                }

                billetera == null && error != null -> Centrado {
                    Text(
                        text = error,
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.size(16.dp))
                    SolventaPrimaryButton(text = "Reintentar", onClick = onReintentar)
                }

                billetera == null || billetera.vacia -> Centrado {
                    Text(
                        text = "Aún no tienes pólizas",
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.size(8.dp))
                    Text(
                        text = "Cuando compres un seguro, su certificado aparecerá aquí.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                    )
                }

                else -> ListaPolizas(billetera = billetera, error = error, onVerPoliza = onVerPoliza)
            }
        }
    }
}

@Composable
private fun EstadoSincronizacion(
    sinConexion: Boolean,
    ultimaSincronizacionMs: Long?,
    datosAntiguos: Boolean,
    falloPersistente: Boolean
) {
    val mensajes = buildList {
        if (datosAntiguos) {
            add("Estos datos tienen más de 30 días y podrían no estar actualizados." to Atencion)
        }
        if (falloPersistente) {
            add("No pudimos actualizar tus pólizas. Volveremos a intentarlo." to Atencion)
        }
    }
    Column(
        modifier = Modifier.padding(horizontal = 24.dp, vertical = 4.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        SyncStatusBanner(
            sinConexion = sinConexion,
            ultimaSincronizacionMs = ultimaSincronizacionMs,
            textoSinConexion = ultimaSincronizacionMs?.let {
                "Sin conexión · Última actualización: ${Formatos.fechaHoraDoceHoras(it)}."
            } ?: "Sin conexión · Mostrando datos guardados."
        )
        mensajes.forEach { (texto, color) ->
            Surface(shape = RoundedCornerShape(12.dp), color = color.copy(alpha = 0.14f)) {
                Text(
                    text = texto,
                    style = MaterialTheme.typography.bodyMedium,
                    color = color,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 10.dp)
                )
            }
        }
    }
}

@Composable
private fun IndicadorConexion(sinConexion: Boolean) {
    val color = if (sinConexion) Offline else Sincronizado
    Icon(
        imageVector = if (sinConexion) Icons.Outlined.CloudOff else Icons.Outlined.CloudDone,
        contentDescription = if (sinConexion) "Sin conexión" else "Datos actualizados",
        tint = color,
        modifier = Modifier
            .padding(end = 12.dp)
            .size(26.dp)
    )
}

@Composable
private fun ListaPolizas(billetera: Billetera, error: String?, onVerPoliza: (String) -> Unit) {
    LazyColumn(
        contentPadding = PaddingValues(start = 24.dp, end = 24.dp, top = 8.dp, bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        if (error != null) {
            item {
                Text(
                    text = error,
                    style = MaterialTheme.typography.bodyMedium,
                    color = Atencion
                )
            }
        }
        // El backend devuelve las pólizas por fecha de emisión, la más reciente arriba.
        items(billetera.polizas, key = { it.polizaId }) { poliza ->
            TarjetaPoliza(poliza = poliza, onClick = { onVerPoliza(poliza.polizaId) })
        }
    }
}

@Composable
private fun TarjetaPoliza(poliza: PolizaResumen, onClick: () -> Unit) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surfaceContainer,
        modifier = Modifier
            .fillMaxWidth()
            .alpha(if (poliza.activa) 1f else 0.6f)
            .clickable(role = Role.Button, onClickLabel = "Ver certificado", onClick = onClick)
    ) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = poliza.nombreRamo,
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                        modifier = Modifier.weight(1f, fill = false)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    EtiquetaEstado(estado = poliza.estado)
                }
                Text(
                    text = "Póliza ${poliza.numeroPoliza}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
                Text(
                    text = Formatos.vigencia(poliza.fechaInicio, poliza.fechaFin),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
                if (poliza.coberturaPrincipal.isNotBlank()) {
                    Text(
                        text = poliza.coberturaPrincipal,
                        style = MaterialTheme.typography.labelMedium,
                        color = Navegacion
                    )
                }
            }
            Icon(
                imageVector = Icons.Filled.ChevronRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)
            )
        }
    }
}

/** La etiqueta lleva el texto del estado: el color nunca es la única señal. */
@Composable
fun EtiquetaEstado(estado: EstadoPoliza, modifier: Modifier = Modifier) {
    val (fondo, texto) = when (estado) {
        EstadoPoliza.VIGENTE -> Avance.copy(alpha = 0.25f) to Color(0xFF2F5A0B)
        EstadoPoliza.VENCIDA -> Atencion.copy(alpha = 0.2f) to Color(0xFF7A3A05)
        EstadoPoliza.CANCELADA -> Color(0xFF8A8F98).copy(alpha = 0.2f) to Color(0xFF3A3D42)
    }
    Surface(shape = RoundedCornerShape(8.dp), color = fondo, modifier = modifier) {
        Text(
            text = Formatos.estado(estado),
            style = MaterialTheme.typography.labelMedium,
            color = texto,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
        )
    }
}

@Composable
internal fun Encabezado(
    titulo: String,
    onVolver: () -> Unit,
    accion: (@Composable () -> Unit)? = null
) {
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
            text = titulo,
            style = MaterialTheme.typography.titleLarge,
            color = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.weight(1f)
        )
        accion?.invoke()
    }
}

@Composable
private fun Centrado(contenido: @Composable () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) { contenido() }
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun WalletScreenPreview() {
    val polizas = listOf(
        PolizaResumen(
            "1", "SOL-VJ-0001", "VIAJE", "Seguro de viaje", EstadoPoliza.VIGENTE, true,
            "2026-10-01", "2026-12-31", "Asistencia médica en viaje", "2026-09-30T14:00:00Z"
        ),
        PolizaResumen(
            "2", "SOL-VD-0002", "VIDA", "Seguro de vida", EstadoPoliza.VENCIDA, false,
            "2025-01-01", "2025-12-31", "Muerte por cualquier causa", "2025-01-01T10:00:00Z"
        )
    )
    SolventaTheme {
        WalletScreen(
            billetera = Billetera(polizas, 1, 1),
            cargando = false,
            error = null,
            onVerPoliza = {},
            onReintentar = {},
            onVolver = {}
        )
    }
}
