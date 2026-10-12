package com.example.solventa.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.R
import com.example.solventa.domain.auth.Perfil
import com.example.solventa.ui.components.SolventaNoticePill
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaSecondaryButton
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.SolventaTheme

/**
 * Primera pantalla con datos del cliente. Solo se compone cuando hay una sesión
 * autenticada (HU02: no se muestra información antes de autenticar).
 */
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
    modifier: Modifier = Modifier
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

    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp)
                .padding(top = 16.dp, bottom = 32.dp),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        painter = painterResource(id = R.drawable.ic_main_page),
                        contentDescription = null,
                        modifier = Modifier.size(20.dp),
                        tint = Navegacion
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Solventa",
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = "Hola, ${perfil.nombre}",
                    style = MaterialTheme.typography.headlineLarge,
                    color = MaterialTheme.colorScheme.onBackground
                )

                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Text(
                            text = "${perfil.nombre} ${perfil.apellido}",
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Text(
                            text = perfil.email,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                        )
                        Text(
                            text = if (biometriaActivada) "Ingreso con huella activado" else "Ingreso con huella desactivado",
                            style = MaterialTheme.typography.labelMedium,
                            color = Navegacion
                        )
                    }
                }

                Text(
                    text = "Tus pólizas aparecerán aquí cuando las adquieras.",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.6f)
                )

                if (mensaje != null) {
                    SolventaNoticePill(text = mensaje, icon = painterResource(id = R.drawable.ic_main_page))
                }
            }

            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                if (!biometriaActivada && biometriaDisponible) {
                    SolventaPrimaryButton(
                        text = "Activar ingreso con huella",
                        onClick = onSolicitarActivacion
                    )
                }

                SolventaSecondaryButton(
                    text = "Cerrar sesión",
                    onClick = onCerrarSesion,
                    isLoading = cerrandoSesion
                )
            }
        }
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun HomeScreenPreview() {
    SolventaTheme {
        HomeScreen(
            perfil = Perfil("u-1", "Ana", "Pérez", "ana@gmail.com", "CLIENTE"),
            biometriaActivada = false,
            biometriaDisponible = true,
            ofrecerActivarBiometria = false,
            mensaje = null,
            cerrandoSesion = false,
            onActivarBiometria = {},
            onSolicitarActivacion = {},
            onDescartarActivacion = {},
            onCerrarSesion = {}
        )
    }
}
