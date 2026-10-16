package com.example.solventa.ui.screens

import android.app.DatePickerDialog
import android.content.Context
import android.graphics.Bitmap
import android.util.Base64
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
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
import com.example.solventa.ui.validation.EDAD_MINIMA
import com.example.solventa.ui.validation.FORMATO_FECHA
import com.example.solventa.ui.validation.TipoDocumento
import com.example.solventa.ui.validation.errorCelular
import com.example.solventa.ui.validation.errorCorreo
import com.example.solventa.ui.validation.errorFechaNacimiento
import com.example.solventa.ui.validation.errorNombre
import com.example.solventa.ui.validation.errorNumeroDocumento
import com.example.solventa.ui.validation.errorPassword
import com.example.solventa.ui.validation.esFormularioRegistroValido
import java.io.ByteArrayOutputStream
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

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
    var menuDocumento by remember { mutableStateOf(false) }
    val contexto = LocalContext.current
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
                onValueChange = { nombre = it.take(100) },
                label = "Nombres",
                placeholder = "Tus nombres",
                keyboardOptions = KeyboardOptions(
                    capitalization = KeyboardCapitalization.Words,
                    imeAction = ImeAction.Next
                ),
                error = errorNombre(nombre, "nombres").takeIf { nombre.isNotBlank() }
            )
            SolventaTextField(
                value = apellido,
                onValueChange = { apellido = it.take(100) },
                label = "Apellidos",
                placeholder = "Tus apellidos",
                keyboardOptions = KeyboardOptions(
                    capitalization = KeyboardCapitalization.Words,
                    imeAction = ImeAction.Next
                ),
                error = errorNombre(apellido, "apellidos").takeIf { apellido.isNotBlank() }
            )

            Box {
                SolventaTextField(
                    value = TipoDocumento.desdeCodigo(tipoDocumento)?.etiqueta.orEmpty(),
                    onValueChange = {},
                    label = "Tipo de documento",
                    placeholder = "Selecciona una opción",
                    readOnly = true,
                    trailingIcon = {
                        Icon(
                            imageVector = Icons.Filled.ArrowDropDown,
                            contentDescription = "Abrir lista de tipos de documento"
                        )
                    }
                )
                Box(
                    modifier = Modifier
                        .matchParentSize()
                        .clickable(enabled = !cargando) { menuDocumento = true }
                )
                DropdownMenu(
                    expanded = menuDocumento,
                    onDismissRequest = { menuDocumento = false }
                ) {
                    TipoDocumento.entries.forEach { tipo ->
                        DropdownMenuItem(
                            text = { Text("${tipo.codigo} · ${tipo.etiqueta}") },
                            onClick = {
                                if (tipo.codigo != tipoDocumento) numeroDocumento = ""
                                tipoDocumento = tipo.codigo
                                menuDocumento = false
                            }
                        )
                    }
                }
            }
            SolventaTextField(
                value = numeroDocumento,
                onValueChange = { nuevo ->
                    val tipo = TipoDocumento.desdeCodigo(tipoDocumento)
                    numeroDocumento = if (tipo?.soloDigitos == false) {
                        nuevo.filter { it.isLetterOrDigit() }.take(12)
                    } else {
                        nuevo.filter { it.isDigit() }.take(12)
                    }
                },
                label = "Número de documento",
                placeholder = if (tipoDocumento == TipoDocumento.PAS.codigo) "Pasaporte" else "Solo números",
                keyboardOptions = KeyboardOptions(
                    keyboardType = if (tipoDocumento == TipoDocumento.PAS.codigo) {
                        KeyboardType.Ascii
                    } else {
                        KeyboardType.Number
                    },
                    imeAction = ImeAction.Next
                ),
                error = if (tipoDocumento.isEmpty()) {
                    null
                } else {
                    errorNumeroDocumento(tipoDocumento, numeroDocumento).takeIf { numeroDocumento.isNotEmpty() }
                }
            )

            Box {
                SolventaTextField(
                    value = fechaNacimiento,
                    onValueChange = {},
                    label = "Fecha de nacimiento",
                    placeholder = "AAAA-MM-DD",
                    readOnly = true,
                    trailingIcon = {
                        Icon(
                            imageVector = Icons.Filled.DateRange,
                            contentDescription = "Seleccionar fecha"
                        )
                    },
                    error = errorFechaNacimiento(fechaNacimiento).takeIf { fechaNacimiento.isNotEmpty() }
                )
                Box(
                    modifier = Modifier
                        .matchParentSize()
                        .clickable(enabled = !cargando) {
                            mostrarSelectorFecha(contexto, fechaNacimiento) { fechaNacimiento = it }
                        }
                )
            }

            SolventaTextField(
                value = email,
                onValueChange = { email = it.trim().take(254) },
                label = "Correo electrónico",
                placeholder = "tu.correo@ejemplo.com",
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Email,
                    imeAction = ImeAction.Next
                ),
                error = errorCorreo(email).takeIf { email.isNotBlank() }
            )
            SolventaTextField(
                value = celular,
                onValueChange = { celular = it.filter { c -> c.isDigit() }.take(10) },
                label = "Celular",
                placeholder = "3001234567",
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Phone,
                    imeAction = ImeAction.Next
                ),
                error = errorCelular(celular).takeIf { celular.isNotEmpty() }
            )
            SolventaTextField(
                value = password,
                onValueChange = { password = it.take(128) },
                label = "Contraseña",
                placeholder = "Mínimo 8 caracteres, letras y números",
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Password,
                    imeAction = ImeAction.Done
                ),
                error = errorPassword(password).takeIf { password.isNotEmpty() }
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
                    text = "Completa todos los campos, usa corrige los campos marcados (mayor de 18 años, celular de 10 dígitos, contraseña con letras y números) y acepta los términos.",
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

/** Abre el calendario del sistema; entrega la fecha ya formateada como AAAA-MM-DD. */
private fun mostrarSelectorFecha(
    contexto: Context,
    actual: String,
    alElegir: (String) -> Unit
) {
    val formato = SimpleDateFormat(FORMATO_FECHA, Locale.US)
    val maxima = Calendar.getInstance().apply { add(Calendar.YEAR, -EDAD_MINIMA) }
    val inicial = Calendar.getInstance().apply {
        time = runCatching { formato.parse(actual) }.getOrNull() ?: maxima.time
    }
    DatePickerDialog(
        contexto,
        { _, anio, mes, dia ->
            val elegida = Calendar.getInstance().apply { set(anio, mes, dia) }
            alElegir(formato.format(elegida.time))
        },
        inicial.get(Calendar.YEAR),
        inicial.get(Calendar.MONTH),
        inicial.get(Calendar.DAY_OF_MONTH)
    ).apply {
        datePicker.maxDate = maxima.timeInMillis
        datePicker.minDate = Calendar.getInstance().apply { add(Calendar.YEAR, -120) }.timeInMillis
    }.show()
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
