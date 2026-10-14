package com.example.solventa.ui.screens

import android.graphics.Bitmap
import android.util.Base64
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material3.Button
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.solventa.domain.auth.DatosRegistro
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaTextField
import com.example.solventa.ui.theme.Atencion
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.Offline
import com.example.solventa.ui.theme.SolventaTheme
import com.example.solventa.ui.validation.canSubmitRegistration
import com.example.solventa.ui.validation.esCorreoValido
import com.example.solventa.ui.validation.esFormularioRegistroValido
import java.io.ByteArrayOutputStream

@Composable
fun RegisterScreen(
    onBackClick: () -> Unit = {},
    onRegisterSubmit: (DatosRegistro) -> Unit = {},
    onLoginClick: () -> Unit = {},
    cargando: Boolean = false,
    mensaje: String? = null,
    modifier: Modifier = Modifier
) {
    var nombre by remember { mutableStateOf("") }
    var apellido by remember { mutableStateOf("") }
    var tipoDocumento by remember { mutableStateOf("") }
    var numeroDocumento by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var celular by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var fechaNacimiento by remember { mutableStateOf("") }
    var aceptaTerminos by remember { mutableStateOf(false) }
    var selfie by remember { mutableStateOf<Bitmap?>(null) }
    var errorCaptura by remember { mutableStateOf<String?>(null) }

    val capturarSelfie = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicturePreview()
    ) { imagen ->
        selfie = imagen
        errorCaptura = if (imagen == null) "No se capturó la selfie. Inténtalo de nuevo." else null
    }

    val formularioValido = esFormularioRegistroValido(
        nombre = nombre,
        apellido = apellido,
        tipoDocumento = tipoDocumento,
        numeroDocumento = numeroDocumento,
        email = email,
        celular = celular,
        password = password,
        fechaNacimiento = fechaNacimiento,
        termsAccepted = aceptaTerminos
    )
    val puedeRegistrar = canSubmitRegistration(
        nombre = nombre,
        apellido = apellido,
        tipoDocumento = tipoDocumento,
        numeroDocumento = numeroDocumento,
        email = email,
        celular = celular,
        password = password,
        fechaNacimiento = fechaNacimiento,
        termsAccepted = aceptaTerminos,
        selfieCaptured = selfie != null
    )

    Surface(
        modifier = modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.surface
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(
                    onClick = onBackClick,
                    modifier = Modifier
                        .background(
                            MaterialTheme.colorScheme.onSurface.copy(alpha = 0.05f),
                            CircleShape
                        )
                ) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.KeyboardArrowLeft,
                        contentDescription = "Volver",
                        tint = MaterialTheme.colorScheme.onSurface
                    )
                }
                Text(
                    text = "Crear cuenta",
                    modifier = Modifier.padding(start = 12.dp),
                    style = MaterialTheme.typography.titleLarge
                )
            }

            Text(
                text = "Cuéntanos sobre ti",
                style = MaterialTheme.typography.headlineLarge,
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = "Completa tus datos y toma una selfie para enviar la verificación.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.65f)
            )

            SolventaTextField(
                value = nombre,
                onValueChange = { nombre = it },
                label = "Nombres",
                placeholder = "Tus nombres",
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next)
            )
            SolventaTextField(
                value = apellido,
                onValueChange = { apellido = it },
                label = "Apellidos",
                placeholder = "Tus apellidos",
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next)
            )
            SolventaTextField(
                value = tipoDocumento,
                onValueChange = { tipoDocumento = it },
                label = "Tipo de documento",
                placeholder = "CC",
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next)
            )
            SolventaTextField(
                value = numeroDocumento,
                onValueChange = { numeroDocumento = it },
                label = "Número de documento",
                placeholder = "Número",
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Number,
                    imeAction = ImeAction.Next
                )
            )
            SolventaTextField(
                value = fechaNacimiento,
                onValueChange = { fechaNacimiento = it },
                label = "Fecha de nacimiento",
                placeholder = "AAAA-MM-DD",
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Ascii,
                    imeAction = ImeAction.Next
                )
            )
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
            if (email.isNotBlank() && !esCorreoValido(email)) {
                Text(
                    text = "Ingresa un correo electrónico válido.",
                    color = Atencion,
                    style = MaterialTheme.typography.bodySmall
                )
            }
            SolventaTextField(
                value = celular,
                onValueChange = { celular = it },
                label = "Celular",
                placeholder = "300 000 0000",
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Phone,
                    imeAction = ImeAction.Next
                )
            )
            SolventaTextField(
                value = password,
                onValueChange = { password = it },
                label = "Contraseña",
                placeholder = "Mínimo 8 caracteres",
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Password,
                    imeAction = ImeAction.Done
                )
            )

            Surface(
                color = Offline.copy(alpha = 0.08f),
                shape = RoundedCornerShape(16.dp)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Checkbox(
                        checked = aceptaTerminos,
                        onCheckedChange = { aceptaTerminos = it },
                        colors = CheckboxDefaults.colors(checkedColor = Navegacion)
                    )
                    Text(
                        text = "Acepto los términos, la política de privacidad y la validación de identidad.",
                        style = MaterialTheme.typography.labelMedium.copy(fontSize = 11.sp)
                    )
                }
            }

            Text(
                text = "Demostración KYC: la selfie se envía al proveedor simulado. No se realiza reconocimiento facial ni prueba de vida real.",
                style = MaterialTheme.typography.bodySmall,
                color = Atencion,
                textAlign = TextAlign.Start
            )

            if (selfie != null) {
                Image(
                    bitmap = selfie!!.asImageBitmap(),
                    contentDescription = "Vista previa de la selfie",
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(220.dp)
                        .clip(RoundedCornerShape(16.dp))
                )
            }

            Button(
                onClick = { capturarSelfie.launch(null) },
                enabled = formularioValido && !cargando,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (selfie == null) "Tomar selfie" else "Tomar otra selfie")
            }

            if (errorCaptura != null || mensaje != null) {
                Text(
                    text = errorCaptura ?: mensaje.orEmpty(),
                    color = Atencion,
                    style = MaterialTheme.typography.bodyMedium
                )
            } else if (!formularioValido) {
                Text(
                    text = "Completa todos los campos, usa una fecha AAAA-MM-DD, una contraseña de al menos 8 caracteres y acepta los términos.",
                    color = Atencion,
                    style = MaterialTheme.typography.bodySmall
                )
            }

            SolventaPrimaryButton(
                text = "Validar identidad y crear cuenta",
                enabled = puedeRegistrar,
                isLoading = cargando,
                onClick = {
                    val imagen = checkNotNull(selfie)
                    onRegisterSubmit(
                        DatosRegistro(
                            nombre = nombre.trim(),
                            apellido = apellido.trim(),
                            email = email.trim(),
                            password = password,
                            tipoDocumento = tipoDocumento.trim(),
                            numeroDocumento = numeroDocumento.trim(),
                            fechaNacimiento = fechaNacimiento.trim(),
                            celular = celular.trim(),
                            selfieBase64 = imagen.aBase64Jpeg()
                        )
                    )
                }
            )

            Text(
                text = "¿Ya tienes cuenta? Iniciar sesión",
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 16.dp)
                    .clickable(enabled = !cargando, onClick = onLoginClick),
                textAlign = TextAlign.Center,
                style = MaterialTheme.typography.bodyMedium.copy(
                    fontWeight = FontWeight.Bold,
                    color = Navegacion
                )
            )
        }
    }
}

private fun Bitmap.aBase64Jpeg(): String {
    val salida = ByteArrayOutputStream()
    check(compress(Bitmap.CompressFormat.JPEG, 75, salida)) {
        "No se pudo codificar la selfie capturada."
    }
    return Base64.encodeToString(salida.toByteArray(), Base64.NO_WRAP)
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun RegisterScreenPreview() {
    SolventaTheme {
        RegisterScreen()
    }
}
