package com.example.solventa.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Autorenew
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.rememberVectorPainter
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.ui.components.SolventaBottomNavigation
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.theme.SolventaTheme

/** Confirmación tras pagar la renovación: la póliza ya tiene la nueva vigencia (HU22). */
@Composable
fun RenewalSuccessScreen(
    onVerPoliza: () -> Unit,
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
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            Encabezado(titulo = "Pólizas", onVolver = onVolver)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Spacer(modifier = Modifier.size(8.dp))
                Box(
                    modifier = Modifier
                        .size(96.dp)
                        .background(Color(0xFFE3F5E9), RoundedCornerShape(24.dp)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Outlined.Autorenew,
                        contentDescription = null,
                        tint = Color(0xFF1B8A4A),
                        modifier = Modifier.size(48.dp)
                    )
                }
                Text(
                    text = "Póliza renovada",
                    style = MaterialTheme.typography.headlineLarge.copy(fontWeight = FontWeight.Bold),
                    color = MaterialTheme.colorScheme.onSurface,
                    textAlign = TextAlign.Center
                )
                Text(
                    text = "Actualizamos la vigencia y el documento ya está disponible.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                    textAlign = TextAlign.Center
                )
                Spacer(modifier = Modifier.size(4.dp))
                SolventaPrimaryButton(
                    text = "Ver póliza renovada",
                    onClick = onVerPoliza,
                    icon = rememberVectorPainter(Icons.Outlined.Shield)
                )
            }
        }
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun RenewalSuccessScreenPreview() {
    SolventaTheme { RenewalSuccessScreen(onVerPoliza = {}, onVolver = {}) }
}
