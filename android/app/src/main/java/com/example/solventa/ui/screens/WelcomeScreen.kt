package com.example.solventa.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.solventa.R
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaSecondaryButton
import com.example.solventa.ui.theme.Avance
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.Noche
import com.example.solventa.ui.theme.Offline
import com.example.solventa.ui.theme.SolventaTheme

@Composable
fun WelcomeScreen(
    onLoginClick: () -> Unit = {},
    onRegisterClick: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.surface
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp, vertical = 32.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {

            // 1. Logo Badge Box
            Box(
                modifier = Modifier
                    .size(120.dp)
                    .background(
                        color = Noche,
                        shape = RoundedCornerShape(36.dp)
                    ),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    painter = painterResource(id = R.drawable.ic_main_page),
                    contentDescription = "Solventa Logo",
                    modifier = Modifier.size(56.dp),
                    tint = Avance
                )
            }

            Spacer(modifier = Modifier.height(20.dp))

            // 2. Brand Subtitle
            Text(
                text = "SOLVENTA",
                style = MaterialTheme.typography.labelMedium.copy(
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.5.sp
                ),
                color = Navegacion
            )

            Spacer(modifier = Modifier.height(16.dp))

            // 3. Main Headline
            Text(
                text = "Tu seguro, cuando lo\nnecesitas.",
                style = MaterialTheme.typography.headlineLarge,
                color = MaterialTheme.colorScheme.onBackground,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(16.dp))

            // 4. Description Body Text
            Text(
                text = "Protección clara para cotizar, comprar y gestionar\ntus seguros desde el celular.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.6f),
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(32.dp))

            // 5. Trust / Verification Badge Pill
            Surface(
                color = Offline.copy(alpha = 0.1f),
                shape = CircleShape
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Center
                ) {
                    Icon(
                        painter = painterResource(id = R.drawable.ic_main_page), // Replace with shield icon if separate
                        contentDescription = null,
                        modifier = Modifier.size(16.dp),
                        tint = Offline
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Identidad verificada y datos protegidos",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                        color = Offline
                    )
                }
            }

            Spacer(modifier = Modifier.height(32.dp))

            // 6. Action Buttons Section
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Primary Action Button (Ingresar)
                SolventaPrimaryButton(
                    text = "Ingresar",
                    onClick = onLoginClick,
                    modifier = Modifier.fillMaxWidth()
                )

                // Secondary Action Button (Crear una cuenta)
                SolventaSecondaryButton(
                    text = "Crear una cuenta",
                    onClick = onRegisterClick,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }
    }
}

// -- Preview Function --
@Preview(showBackground = true, showSystemUi = true)
@Composable
fun WelcomeScreenPreview() {
    SolventaTheme {
        WelcomeScreen()
    }
}