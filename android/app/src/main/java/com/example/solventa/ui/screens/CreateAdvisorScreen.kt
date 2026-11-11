package com.example.solventa.ui.screens

import android.app.DatePickerDialog
import android.content.Context
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.asesor.DatosNuevoAsesor
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaTextField
import com.example.solventa.ui.theme.Atencion
import com.example.solventa.ui.theme.Avance
import com.example.solventa.ui.theme.SolventaTheme
import com.example.solventa.ui.validation.TipoDocumento
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

/**
 * Alta de un asesor de ventas (HU20), accesible solo para un manager (SERVICIO_INTERNO).
 * El rol y el consentimiento de identidad los fija la capa de datos.
 */
@Composable
fun CreateAdvisorScreen(
    creando: Boolean,
    error: String?,
    creadoNombre: String?,
    onCrear: (DatosNuevoAsesor) -> Unit,
    onVolver: () -> Unit,
    onHecho: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
        Column(modifier = Modifier.fillMaxSize()) {
            Encabezado(titulo = "Crear asesor de ventas", onVolver = onVolver)

            if (creadoNombre != null) {
                ConfirmacionAsesor(nombre = creadoNombre, onHecho = onHecho)
            } else {
                Formulario(creando = creando, error = error, onCrear = onCrear)
            }
        }
    }
}

@Composable
private fun Formulario(
    creando: Boolean,
    error: String?,
    onCrear: (DatosNuevoAsesor) -> Unit
) {
    var nombre by remember { mutableStateOf("") }
    var apellido by remember { mutableStateOf("") }
    var tipoDocumento by remember { mutableStateOf("CC") }
    var numeroDocumento by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var confirmar by remember { mutableStateOf("") }
    var fechaNacimiento by remember { mutableStateOf("") }
    var menuDocumento by remember { mutableStateOf(false) }
    var errorLocal by remember { mutableStateOf<String?>(null) }
    val contexto = LocalContext.current

    val puedeEnviar = nombre.isNotBlank() && apellido.isNotBlank() &&
        numeroDocumento.isNotBlank() && email.isNotBlank() &&
        password.length >= 8 && fechaNacimiento.isNotBlank()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text(
            text = "Con su cuenta podrá asociar clientes y registrar siniestros en su nombre.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
        )

        SolventaTextField(
            value = nombre,
            onValueChange = { nombre = it.take(100) },
            label = "Nombres",
            placeholder = "Nombres del asesor",
            keyboardOptions = KeyboardOptions(
                capitalization = KeyboardCapitalization.Words,
                imeAction = ImeAction.Next
            )
        )
        SolventaTextField(
            value = apellido,
            onValueChange = { apellido = it.take(100) },
            label = "Apellidos",
            placeholder = "Apellidos del asesor",
            keyboardOptions = KeyboardOptions(
                capitalization = KeyboardCapitalization.Words,
                imeAction = ImeAction.Next
            )
        )

        Box {
            SolventaTextField(
                value = TipoDocumento.desdeCodigo(tipoDocumento)?.etiqueta.orEmpty(),
                onValueChange = {},
                label = "Tipo de documento",
                placeholder = "Selecciona una opción",
                readOnly = true,
                trailingIcon = {
                    Icon(Icons.Filled.ArrowDropDown, contentDescription = "Abrir lista")
                }
            )
            Box(
                modifier = Modifier
                    .matchParentSize()
                    .clickable(enabled = !creando) { menuDocumento = true }
            )
            DropdownMenu(expanded = menuDocumento, onDismissRequest = { menuDocumento = false }) {
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
            placeholder = "Documento del asesor",
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number, imeAction = ImeAction.Next)
        )

        Box {
            SolventaTextField(
                value = fechaNacimiento,
                onValueChange = {},
                label = "Fecha de nacimiento",
                placeholder = "AAAA-MM-DD",
                readOnly = true,
                trailingIcon = {
                    Icon(Icons.Filled.DateRange, contentDescription = "Seleccionar fecha")
                }
            )
            Box(
                modifier = Modifier
                    .matchParentSize()
                    .clickable(enabled = !creando) {
                        mostrarSelectorFechaAsesor(contexto, fechaNacimiento) { fechaNacimiento = it }
                    }
            )
        }

        SolventaTextField(
            value = email,
            onValueChange = { email = it.trim().take(254) },
            label = "Correo corporativo",
            placeholder = "asesor@solventa.com",
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email, imeAction = ImeAction.Next)
        )
        SolventaTextField(
            value = password,
            onValueChange = { password = it.take(128) },
            label = "Contraseña",
            placeholder = "Mínimo 8 caracteres",
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = ImeAction.Next)
        )
        SolventaTextField(
            value = confirmar,
            onValueChange = { confirmar = it.take(128) },
            label = "Confirmar contraseña",
            placeholder = "Repite la contraseña",
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = ImeAction.Done)
        )

        val mensajeError = errorLocal ?: error
        if (mensajeError != null) {
            Text(text = mensajeError, style = MaterialTheme.typography.bodyMedium, color = Atencion)
        }

        Spacer(modifier = Modifier.size(4.dp))
        SolventaPrimaryButton(
            text = "Crear asesor",
            onClick = {
                errorLocal = when {
                    password.length < 8 -> "La contraseña debe tener mínimo 8 caracteres."
                    password != confirmar -> "Las contraseñas no coinciden."
                    else -> null
                }
                if (errorLocal == null && puedeEnviar) {
                    onCrear(
                        DatosNuevoAsesor(
                            nombre = nombre.trim(),
                            apellido = apellido.trim(),
                            email = email.trim(),
                            password = password,
                            tipoDocumento = tipoDocumento.trim(),
                            numeroDocumento = numeroDocumento.trim(),
                            fechaNacimiento = fechaNacimiento.trim()
                        )
                    )
                }
            },
            enabled = !creando && puedeEnviar,
            isLoading = creando
        )
        Spacer(modifier = Modifier.size(24.dp))
    }
}

@Composable
private fun ConfirmacionAsesor(nombre: String, onHecho: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = Icons.Filled.CheckCircle,
            contentDescription = null,
            tint = Avance,
            modifier = Modifier.size(56.dp)
        )
        Spacer(modifier = Modifier.size(16.dp))
        Text(
            text = "Asesor creado",
            style = MaterialTheme.typography.titleLarge,
            color = MaterialTheme.colorScheme.onSurface
        )
        Spacer(modifier = Modifier.size(8.dp))
        Text(
            text = "$nombre ya puede iniciar sesión como asesor de ventas.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
        )
        Spacer(modifier = Modifier.size(24.dp))
        SolventaPrimaryButton(text = "Volver al inicio", onClick = onHecho)
    }
}

/** Calendario del sistema para la fecha de nacimiento; entrega AAAA-MM-DD. */
private fun mostrarSelectorFechaAsesor(
    contexto: Context,
    actual: String,
    alElegir: (String) -> Unit
) {
    val formato = SimpleDateFormat("yyyy-MM-dd", Locale.US)
    val maxima = Calendar.getInstance().apply { add(Calendar.YEAR, -18) }
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

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun CreateAdvisorScreenPreview() {
    SolventaTheme {
        CreateAdvisorScreen(
            creando = false,
            error = null,
            creadoNombre = null,
            onCrear = {},
            onVolver = {},
            onHecho = {}
        )
    }
}
