package com.example.solventa.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.R
import com.example.solventa.ui.components.SolventaNoticePill
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaSecondaryButton
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.SolventaTheme

@Composable
fun BiometricalLoginScreen(
    onBackClick: () -> Unit = {},
    onBiometricClick: () -> Unit = {},
    onUseCredentialsClick: () -> Unit = {},
    onRegisterClick: () -> Unit = {},
    biometriaDisponible: Boolean = true,
    cargando: Boolean = false,
    mensaje: String? = null,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.surface
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp)
                .padding(top = 16.dp, bottom = 32.dp),
            verticalArrangement = Arrangement.SpaceBetween,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // 1. Top Bar: Back Button & Header Title
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(
                    onClick = onBackClick,
                    modifier = Modifier
                        .size(40.dp)
                        .background(
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.05f),
                            shape = CircleShape
                        )
                ) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.KeyboardArrowLeft,
                        contentDescription = "Volver",
                        tint = MaterialTheme.colorScheme.onSurface
                    )
                }

                Spacer(modifier = Modifier.width(12.dp))

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

            // 2. Main Middle Section: Icon, Copy, and Info Card
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.fillMaxWidth()
            ) {
                // Fingerprint Hero Icon Box
                Box(
                    modifier = Modifier
                        .size(128.dp)
                        .background(
                            color = Color(0xFFEEF2FF), // Light soft blue container
                            shape = RoundedCornerShape(36.dp)
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        painter = painterResource(id = R.drawable.ic_main_page), // Replace with R.drawable.ic_fingerprint if separate
                        contentDescription = "Huella dactilar",
                        modifier = Modifier.size(56.dp),
                        tint = Navegacion
                    )
                }

                Spacer(modifier = Modifier.height(28.dp))

                // Headline Title
                Text(
                    text = "Hola de nuevo",
                    style = MaterialTheme.typography.headlineLarge,
                    color = MaterialTheme.colorScheme.onBackground,
                    textAlign = TextAlign.Center
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Subtitle Description
                Text(
                    text = "Usa la huella configurada en tu dispositivo para entrar de forma rápida y segura.",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.6f),
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(horizontal = 12.dp)
                )

                Spacer(modifier = Modifier.height(24.dp))

                // Security Banner Pill
                Surface(
                    color = Color(0xFFE6F4EA), // Soft green banner background
                    shape = RoundedCornerShape(16.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Outlined.Lock,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp),
                            tint = Color(0xFF137333) // Dark green tint
                        )

                        Spacer(modifier = Modifier.width(12.dp))

                        Text(
                            text = "La huella se valida en el dispositivo y no se almacena en Solventa.",
                            style = MaterialTheme.typography.labelMedium.copy(
                                fontWeight = FontWeight.Normal,
                                color = Color(0xFF137333)
                            )
                        )
                    }
                }
            }

            // 3. Bottom Actions: Buttons & Text Link
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                if (mensaje != null) {
                    SolventaNoticePill(
                        text = mensaje,
                        icon = painterResource(id = R.drawable.ic_main_page)
                    )
                }

                SolventaPrimaryButton(
                    text = "Ingresar con biometría",
                    onClick = onBiometricClick,
                    enabled = biometriaDisponible,
                    isLoading = cargando
                )

                SolventaSecondaryButton(
                    text = "Usar correo y contraseña",
                    onClick = onUseCredentialsClick
                )

                Spacer(modifier = Modifier.height(4.dp))

                // Inline Styled Link Text
                Text(
                    text = buildAnnotatedString {
                        append("¿Aún no tienes cuenta? ")
                        withStyle(
                            style = SpanStyle(
                                color = Navegacion,
                                fontWeight = FontWeight.Bold
                            )
                        ) {
                            append("Crear una")
                        }
                    },
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.7f),
                    modifier = Modifier.clickable { onRegisterClick() }
                )
            }
        }
    }
}

// -- Preview Function --
@Preview(showBackground = true, showSystemUi = true)
@Composable
fun LoginScreenPreview() {
    SolventaTheme {
        BiometricalLoginScreen()
    }
}