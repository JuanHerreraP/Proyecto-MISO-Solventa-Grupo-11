package com.example.solventa.ui.screens

import androidx.compose.foundation.background
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Payments
import androidx.compose.material.icons.outlined.ReportProblem
import androidx.compose.material.icons.outlined.Schedule
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.notificaciones.Bandeja
import com.example.solventa.domain.notificaciones.Notificacion
import com.example.solventa.domain.notificaciones.TipoNotificacion
import com.example.solventa.domain.polizas.Formatos
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.theme.Atencion
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.SolventaTheme
import com.example.solventa.R
import com.example.solventa.i18n.tr

/**
 * Bandeja de notificaciones (HU05): todos los eventos registrados, también los que llegaron con el
 * push deshabilitado. Al tocar uno se abre su destino y queda como leído.
 */
@Composable
fun NotificationsScreen(
    bandeja: Bandeja?,
    cargando: Boolean,
    error: String?,
    onReintentar: () -> Unit,
    onVolver: () -> Unit,
    onAbrir: (Notificacion) -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
        Column(modifier = Modifier.fillMaxSize()) {
            Encabezado(titulo = tr(R.string.home_notificaciones), onVolver = onVolver)

            when {
                bandeja == null && cargando -> Centrado {
                    CircularProgressIndicator(
                        color = Navegacion,
                        modifier = Modifier.semantics {
                            contentDescription = tr(R.string.notifications_cargando_tus_notificaciones)
                        }
                    )
                }

                bandeja == null && error != null -> Centrado {
                    Text(
                        text = error,
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.size(16.dp))
                    SolventaPrimaryButton(text = tr(R.string.assistance_reintentar), onClick = onReintentar)
                }

                bandeja == null || bandeja.vacia -> Centrado {
                    Text(
                        text = tr(R.string.notifications_aun_no_tienes_notificaciones),
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.size(8.dp))
                    Text(
                        text = tr(R.string.notifications_aqui_veras_los_avisos_sobre),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                    )
                }

                else -> ListaNotificaciones(bandeja, error, onAbrir)
            }
        }
    }
}

@Composable
private fun ListaNotificaciones(
    bandeja: Bandeja,
    error: String?,
    onAbrir: (Notificacion) -> Unit
) {
    LazyColumn(
        contentPadding = PaddingValues(start = 24.dp, end = 24.dp, top = 8.dp, bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        if (error != null) {
            item { Text(text = error, style = MaterialTheme.typography.bodyMedium, color = Atencion) }
        }
        item {
            Text(
                text = if (bandeja.noLeidas == 0) {
                    tr(R.string.notifications_estas_al_dia)
                } else {
                    tr(R.string.notifications_sin_leer, bandeja.noLeidas)
                },
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
            )
        }
        items(bandeja.notificaciones, key = { it.notificacionId }) { notificacion ->
            TarjetaNotificacion(notificacion, onClick = { onAbrir(notificacion) })
        }
    }
}

@Composable
private fun TarjetaNotificacion(notificacion: Notificacion, onClick: () -> Unit) {
    val sinLeer = !notificacion.leida
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = if (sinLeer) Navegacion.copy(alpha = 0.08f)
        else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
        modifier = Modifier
            .fillMaxWidth()
            .semantics { if (sinLeer) stateDescription = tr(R.string.notifications_sin_leer_2) }
            .clickable(role = Role.Button, onClickLabel = tr(R.string.notifications_abrir_notificacion), onClick = onClick)
    ) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.Top) {
            Surface(shape = RoundedCornerShape(12.dp), color = Navegacion.copy(alpha = 0.12f)) {
                Icon(
                    imageVector = icono(notificacion.tipo),
                    contentDescription = null,
                    tint = Navegacion,
                    modifier = Modifier
                        .padding(10.dp)
                        .size(22.dp)
                )
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = notificacion.titulo,
                    style = MaterialTheme.typography.titleSmall.copy(
                        fontWeight = if (sinLeer) FontWeight.Bold else FontWeight.Medium
                    ),
                    color = MaterialTheme.colorScheme.onSurface
                )
                Text(
                    text = notificacion.cuerpo,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f)
                )
                Text(
                    text = Formatos.fechaHora(notificacion.creadaEn),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f)
                )
            }
            if (sinLeer) {
                Spacer(modifier = Modifier.width(8.dp))
                // El punto acompaña a la descripción "Sin leer": el color no es la única señal.
                Box(
                    modifier = Modifier
                        .padding(top = 6.dp)
                        .size(10.dp)
                        .background(Navegacion, CircleShape)
                )
            }
        }
    }
}

private fun icono(tipo: TipoNotificacion): ImageVector = when (tipo) {
    TipoNotificacion.PAGO_PARAMETRICO -> Icons.Outlined.Payments
    TipoNotificacion.VENCIMIENTO_POLIZA -> Icons.Outlined.Schedule
    TipoNotificacion.ESTADO_SINIESTRO -> Icons.Outlined.ReportProblem
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
fun NotificationsScreenPreview() {
    SolventaTheme {
        NotificationsScreen(
            bandeja = Bandeja(
                notificaciones = listOf(
                    Notificacion(
                        "NOT-1", TipoNotificacion.PAGO_PARAMETRICO,
                        "Aprobamos el pago de tu seguro paramétrico",
                        "Se aprobó un pago de \$500.000 COP por tu póliza SOL-PM-000001.",
                        mapOf("siniestro_id" to "SIN-1"), "2026-12-10T15:00:00Z", false
                    ),
                    Notificacion(
                        "NOT-2", TipoNotificacion.VENCIMIENTO_POLIZA,
                        "Tu póliza está por vencer",
                        "Tu póliza SOL-VD-000001 vence en 15 días. Renuévala para mantener tu cobertura.",
                        mapOf("poliza_id" to "POL-1"), "2026-12-09T15:00:00Z", true
                    )
                ),
                noLeidas = 1
            ),
            cargando = false,
            error = null,
            onReintentar = {},
            onVolver = {},
            onAbrir = {}
        )
    }
}
