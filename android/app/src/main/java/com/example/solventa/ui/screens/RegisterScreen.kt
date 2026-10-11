package com.example.solventa.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaTextField
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.Offline
import com.example.solventa.ui.theme.SolventaTheme

@Composable
fun RegisterScreen(
    onBackClick: () -> Unit = {},
    onRegisterSubmit: () -> Unit = {},
    onLoginClick: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    var fullName by remember { mutableStateOf("") }
    var documentType by remember { mutableStateOf("") }
    var documentNumber by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var termsAccepted by remember { mutableStateOf(false) }

    Surface(
        modifier = modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.surface
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp)
                .padding(top = 16.dp, bottom = 24.dp),
            verticalArrangement = Arrangement.SpaceBetween,
            horizontalAlignment = Alignment.Start
        ) {
            // 1. Top Bar & Header Section
            Column(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
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

                        Spacer(modifier = Modifier.width(16.dp))

                        Text(
                            text = "Crear cuenta",
                            style = MaterialTheme.typography.titleLarge,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }

                    Text(
                        text = "PASO 1 DE 2",
                        style = MaterialTheme.typography.labelSmall.copy(
                            fontWeight = FontWeight.Bold,
                            fontSize = 11.sp
                        ),
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                Text(
                    text = "REGISTRO",
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontWeight = FontWeight.Bold,
                        color = Navegacion,
                        fontSize = 11.sp
                    )
                )

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = "Cuéntanos sobre ti",
                    style = MaterialTheme.typography.headlineLarge,
                    color = MaterialTheme.colorScheme.onBackground
                )

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = "Usaremos estos datos para crear y proteger tu cuenta.",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.6f)
                )
            }

            // 2. Scrollable / Stacked Form Fields
            Column(
                verticalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                // Nombres y Apellidos
                SolventaTextField(
                    value = fullName,
                    onValueChange = { fullName = it },
                    label = "Nombres y apellidos",
                    placeholder = "Tu nombre completo",
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next)
                )

                // Document Type & Number Row
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Box(modifier = Modifier.weight(0.45f)) {
                        SolventaTextField(
                            value = documentType,
                            onValueChange = { documentType = it },
                            label = "Tipo de documento",
                            placeholder = "Cédula",
                            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next)
                        )
                    }
                    Box(modifier = Modifier.weight(0.55f)) {
                        SolventaTextField(
                            value = documentNumber,
                            onValueChange = { documentNumber = it },
                            label = "Número",
                            placeholder = "Número de documento",
                            keyboardOptions = KeyboardOptions(
                                keyboardType = KeyboardType.Number,
                                imeAction = ImeAction.Next
                            )
                        )
                    }
                }

                // Correo Electrónico
                SolventaTextField(
                    value = email,
                    onValueChange = { email = it },
                    label = "Correo electrónico",
                    placeholder = "tu.correo@ejemplo.com",
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Email,
                        imeAction = ImeAction.Next
                    )
                )

                // Celular
                SolventaTextField(
                    value = phone,
                    onValueChange = { phone = it },
                    label = "Celular",
                    placeholder = "300 000 0000",
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Phone,
                        imeAction = ImeAction.Next
                    )
                )

                // Contraseña
                SolventaTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = "Contraseña",
                    placeholder = "••••••••",
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Password,
                        imeAction = ImeAction.Done
                    )
                )

                // Terms & Conditions Banner Box
                Surface(
                    color = Offline.copy(alpha = 0.08f),
                    shape = RoundedCornerShape(16.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 8.dp, vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Checkbox(
                            checked = termsAccepted,
                            onCheckedChange = { termsAccepted = it },
                            colors = CheckboxDefaults.colors(
                                checkedColor = Navegacion
                            )
                        )
                        Text(
                            text = "Acepto los términos, la política de privacidad y el tratamiento de datos.",
                            style = MaterialTheme.typography.labelMedium.copy(
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f)
                            ),
                            modifier = Modifier.padding(end = 12.dp)
                        )
                    }
                }
            }

            // 3. Bottom Action Button & Login Link
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                SolventaPrimaryButton(
                    text = "Continuar",
                    enabled = termsAccepted && email.isNotBlank() && password.isNotBlank(),
                    onClick = onRegisterSubmit
                )

                Text(
                    text = "¿Ya tienes cuenta? Iniciar sesión",
                    style = MaterialTheme.typography.bodyMedium.copy(
                        fontWeight = FontWeight.Bold,
                        color = Navegacion
                    ),
                    textAlign = TextAlign.Center,
                    modifier = Modifier.clickable { onLoginClick() }
                )
            }
        }
    }
}

// -- Preview Function --
@Preview(showBackground = true, showSystemUi = true)
@Composable
fun RegisterScreenPreview() {
    SolventaTheme {
        RegisterScreen()
    }
}