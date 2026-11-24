package com.example.solventa.ui.screens

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CloudOff
import androidx.compose.material.icons.outlined.Sync
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.text.font.FontWeight
import com.example.solventa.ui.theme.Atencion
import com.example.solventa.ui.theme.Avance
import com.example.solventa.ui.theme.Offline
import com.example.solventa.ui.theme.Sincronizado
import kotlinx.coroutines.delay
import com.example.solventa.R
import com.example.solventa.i18n.tr

@Composable
internal fun SyncStatusBanner(
    sinConexion: Boolean,
    ultimaSincronizacionMs: Long?,
    textoSinConexion: String = tr(R.string.sync_status_banner_datos_disponibles_sin_conexion),
    textoSincronizado: String = tr(R.string.sync_status_banner_actualizado),
    modifier: Modifier = Modifier
) {
    if (!sinConexion && ultimaSincronizacionMs == null) return

    val ahoraMs = rememberAhoraSincronizacion(ultimaSincronizacionMs)

    val color = if (sinConexion) Offline else Sincronizado
    val texto = if (sinConexion) {
        textoSinConexion
    } else {
        "$textoSincronizado ${tiempoTranscurrido(ultimaSincronizacionMs!!, ahoraMs)}."
    }
    val icono = if (sinConexion) Icons.Outlined.CloudOff else Icons.Outlined.Sync

    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        color = color.copy(alpha = 0.13f)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 13.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = icono,
                contentDescription = null,
                tint = color,
                modifier = Modifier.size(21.dp)
            )
            Spacer(modifier = Modifier.width(10.dp))
            Text(
                text = texto,
                style = MaterialTheme.typography.bodyMedium,
                color = color
            )
        }
    }
}

@Composable
internal fun InlineSyncStatus(
    sinConexion: Boolean,
    ultimaSincronizacionMs: Long?
) {
    if (!sinConexion && ultimaSincronizacionMs == null) return

    val ahoraMs = rememberAhoraSincronizacion(ultimaSincronizacionMs)
    val color = if (sinConexion) Atencion else Avance
    val texto = if (sinConexion) {
        tr(R.string.sync_status_banner_sin_conexion_mostrando_datos_guardados)
    } else {
        tr(R.string.sync_status_banner_actualizado_2, tiempoTranscurrido(ultimaSincronizacionMs!!, ahoraMs))
    }

    Row(verticalAlignment = Alignment.CenterVertically) {
        Surface(shape = RoundedCornerShape(50), color = color) {
            Spacer(modifier = Modifier.size(10.dp))
        }
        Spacer(modifier = Modifier.width(10.dp))
        Text(
            text = texto,
            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
            color = color
        )
    }
}

@Composable
private fun rememberAhoraSincronizacion(ultimaSincronizacionMs: Long?): Long {
    var ahoraMs by remember(ultimaSincronizacionMs) {
        mutableLongStateOf(System.currentTimeMillis())
    }
    LaunchedEffect(ultimaSincronizacionMs) {
        while (true) {
            delay(60_000L)
            ahoraMs = System.currentTimeMillis()
        }
    }
    return ahoraMs
}

internal fun tiempoTranscurrido(
    instanteMs: Long,
    ahoraMs: Long = System.currentTimeMillis()
): String {
    val minutos = ((ahoraMs - instanteMs).coerceAtLeast(0L) / 60_000L)
    return when {
        minutos < 1 -> tr(R.string.sync_status_banner_ahora)
        minutos < 60 -> tr(R.string.sync_status_banner_hace_min, minutos)
        minutos < 120 -> tr(R.string.sync_status_banner_hace_1_h)
        minutos < 1_440 -> tr(R.string.sync_status_banner_hace_h, minutos / 60)
        minutos < 2_880 -> tr(R.string.sync_status_banner_hace_1_dia)
        else -> tr(R.string.sync_status_banner_hace_dias, minutos / 1_440)
    }
}
