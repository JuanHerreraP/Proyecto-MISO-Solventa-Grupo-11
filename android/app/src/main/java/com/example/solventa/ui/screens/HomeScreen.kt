package com.example.solventa.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.automirrored.outlined.Logout
import androidx.compose.material.icons.outlined.LocationOn
import androidx.compose.material.icons.outlined.NotificationsNone
import androidx.compose.material.icons.outlined.RequestQuote
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.VerifiedUser
import androidx.compose.material.icons.outlined.WarningAmber
import androidx.compose.material3.AlertDialog
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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.rememberVectorPainter
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.auth.Perfil
import com.example.solventa.ui.components.SolventaNoticePill
import com.example.solventa.ui.components.SolventaBottomNavigation
import com.example.solventa.ui.theme.Avance
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.Noche
import com.example.solventa.ui.theme.Offline
import com.example.solventa.ui.theme.SolventaTheme

/** Inicio privado del cliente. Conserva las funciones de sesión y billetera. */
@Composable
fun HomeScreen(
    perfil: Perfil,
    biometriaActivada: Boolean,
    biometriaDisponible: Boolean,
    ofrecerActivarBiometria: Boolean,
    mensaje: String?,
    cerrandoSesion: Boolean,
    onActivarBiometria: () -> Unit,
    onSolicitarActivacion: () -> Unit,
    onDescartarActivacion: () -> Unit,
    onCerrarSesion: () -> Unit,
    modifier: Modifier = Modifier,
    onVerBilletera: (() -> Unit)? = null,
    onVerCotizaciones: (() -> Unit)? = null,
    onCotizarSeguro: () -> Unit = {},
    cantidadPolizasActivas: Int? = null
) {
    if (ofrecerActivarBiometria) {
        AlertDialog(
            onDismissRequest = onDescartarActivacion,
            title = { Text("¿Activar ingreso con huella?") },
            text = {
                Text(
                    "La próxima vez podrás entrar con la huella o el rostro configurados en tu dispositivo. " +
                        "Tu biometría no sale del teléfono."
                )
            },
            confirmButton = { TextButton(onClick = onActivarBiometria) { Text("Activar") } },
            dismissButton = { TextButton(onClick = onDescartarActivacion) { Text("Ahora no") } }
        )
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        bottomBar = { SolventaBottomNavigation(onPolizas = onVerBilletera) }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            EncabezadoInicio()

            Text(
                text = "Hola, ${perfil.nombre}",
                style = MaterialTheme.typography.headlineLarge,
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = "Todo lo importante de tu protección, en un solo lugar.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
            )

            TarjetaBilletera(
                cantidadPolizasActivas = cantidadPolizasActivas,
                onVerBilletera = onVerBilletera,
                onCotizarSeguro = onCotizarSeguro
            )

            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                AccionInicio(
                    titulo = "Ver pólizas",
                    icono = Icons.Outlined.VerifiedUser,
                    onClick = onVerBilletera,
                    modifier = Modifier.weight(1f)
                )
                AccionInicio(
                    titulo = "Ver cotizaciones",
                    icono = Icons.Outlined.RequestQuote,
                    onClick = onVerCotizaciones,
                    modifier = Modifier.weight(1f)
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                AccionInicio(
                    titulo = "Reportar siniestro",
                    icono = Icons.Outlined.WarningAmber,
                    modifier = Modifier.weight(1f)
                )
                AccionInicio(
                    titulo = "Pedir asistencia",
                    icono = Icons.Outlined.LocationOn,
                    modifier = Modifier.weight(1f)
                )
            }

            Surface(shape = RoundedCornerShape(24.dp), color = Offline.copy(alpha = 0.15f)) {
                Row(
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Surface(shape = RoundedCornerShape(50), color = Offline) {
                        Spacer(modifier = Modifier.size(9.dp))
                    }
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(
                        text = "Datos disponibles sin conexión",
                        style = MaterialTheme.typography.bodyMedium,
                        color = Offline
                    )
                }
            }

            if (mensaje != null) {
                SolventaNoticePill(
                    text = mensaje,
                    icon = rememberVectorPainter(Icons.Outlined.Shield)
                )
            }

            if (!biometriaActivada && biometriaDisponible) {
                TextButton(onClick = onSolicitarActivacion) {
                    Text("Activar ingreso con huella", color = Navegacion)
                }
            }

            TextButton(
                onClick = onCerrarSesion,
                enabled = !cerrandoSesion,
                modifier = Modifier.align(Alignment.CenterHorizontally)
            ) {
                Icon(Icons.AutoMirrored.Outlined.Logout, contentDescription = null, tint = Navegacion)
                Spacer(modifier = Modifier.width(8.dp))
                Text(if (cerrandoSesion) "Cerrando sesión…" else "Cerrar sesión", color = Navegacion)
            }
        }
    }
}

@Composable
private fun EncabezadoInicio() {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = Icons.Outlined.Shield,
                contentDescription = null,
                modifier = Modifier.size(24.dp),
                tint = Navegacion
            )
            Spacer(modifier = Modifier.width(10.dp))
            Text(
                text = "Solventa",
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.onSurface
            )
        }
        IconButton(onClick = {}) {
            Icon(
                imageVector = Icons.Outlined.NotificationsNone,
                contentDescription = "Notificaciones",
                tint = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}

@Composable
private fun TarjetaBilletera(
    cantidadPolizasActivas: Int?,
    onVerBilletera: (() -> Unit)?,
    onCotizarSeguro: () -> Unit
) {
    Surface(
        shape = RoundedCornerShape(24.dp),
        color = Noche,
        modifier = Modifier
            .fillMaxWidth()
            .then(
                if (onVerBilletera == null) Modifier else Modifier.clickable(
                    role = Role.Button,
                    onClickLabel = "Ver mi billetera",
                    onClick = onVerBilletera
                )
            )
    ) {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                text = "Billetera de pólizas",
                style = MaterialTheme.typography.bodyMedium,
                color = Color.White.copy(alpha = 0.7f)
            )
            Text(
                text = textoPolizas(cantidadPolizasActivas),
                style = MaterialTheme.typography.headlineMedium,
                color = Color.White
            )
            if (cantidadPolizasActivas != null) {
                Text(
                    text = "●  Actualizado recientemente",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Avance
                )
            }
            if (onVerBilletera != null) {
                Text(
                    text = "Ver mi billetera",
                    style = MaterialTheme.typography.labelMedium,
                    color = Color.White.copy(alpha = 0.75f)
                )
            }
            Row(
                modifier = Modifier
                    .clickable(role = Role.Button, onClick = onCotizarSeguro)
                    .padding(vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Cotizar un nuevo seguro",
                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                    color = Color.White
                )
                Spacer(modifier = Modifier.width(6.dp))
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp),
                    tint = Color.White
                )
            }
        }
    }
}

private fun textoPolizas(cantidad: Int?): String = when (cantidad) {
    null -> "Consulta tus pólizas"
    1 -> "1 póliza activa"
    else -> "$cantidad pólizas activas"
}

@Composable
private fun AccionInicio(
    titulo: String,
    icono: ImageVector,
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null
) {
    Surface(
        modifier = modifier
            .height(108.dp)
            .then(
                if (onClick == null) Modifier else Modifier.clickable(
                    role = Role.Button,
                    onClick = onClick
                )
            ),
        shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f))
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Surface(shape = RoundedCornerShape(12.dp), color = Navegacion.copy(alpha = 0.1f)) {
                Icon(
                    imageVector = icono,
                    contentDescription = null,
                    tint = Navegacion,
                    modifier = Modifier.padding(10.dp).size(22.dp)
                )
            }
            Text(
                text = titulo,
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun HomeScreenPreview() {
    SolventaTheme {
        HomeScreen(
            perfil = Perfil("u-1", "Ana", "Pérez", "ana@gmail.com", "CLIENTE"),
            biometriaActivada = true,
            biometriaDisponible = true,
            ofrecerActivarBiometria = false,
            mensaje = null,
            cerrandoSesion = false,
            onActivarBiometria = {},
            onSolicitarActivacion = {},
            onDescartarActivacion = {},
            onCerrarSesion = {},
            onVerBilletera = {},
            onVerCotizaciones = {},
            onCotizarSeguro = {},
            cantidadPolizasActivas = 2
        )
    }
}
