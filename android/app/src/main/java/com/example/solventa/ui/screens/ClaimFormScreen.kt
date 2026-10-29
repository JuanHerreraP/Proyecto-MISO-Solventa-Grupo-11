package com.example.solventa.ui.screens

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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.SelectableDates
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TimePicker
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.material3.rememberTimePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.polizas.Formatos
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaTextField
import com.example.solventa.ui.theme.Atencion
import com.example.solventa.ui.theme.SolventaTheme
import com.example.solventa.ui.validation.errorDescripcionSiniestro
import com.example.solventa.ui.validation.errorEstimacionSiniestro
import com.example.solventa.ui.validation.errorFechaSiniestro
import com.example.solventa.ui.validation.errorHoraSiniestro
import com.example.solventa.ui.validation.errorLugarSiniestro
import com.example.solventa.ui.validation.errorPolizaSiniestro
import com.example.solventa.ui.validation.esFormularioSiniestroValido
import com.example.solventa.ui.validation.normalizarEstimacion
import java.util.Calendar

/** Una póliza elegible para reportar un siniestro: id y una etiqueta legible. */
data class PolizaElegible(val polizaId: String, val etiqueta: String)

/**
 * Formulario de registro manual de siniestros (HU20). El cliente elige una de sus pólizas
 * vigentes (o ingresa el número si no hay lista) y describe el evento. El backend valida la
 * vigencia y la titularidad de forma autoritativa.
 */
@Composable
fun ClaimFormScreen(
    polizas: List<PolizaElegible>,
    registrando: Boolean,
    error: String?,
    onRegistrar: (polizaId: String, fecha: String, hora: String, lugar: String, descripcion: String, estimacion: String) -> Unit,
    onVolver: () -> Unit,
    modifier: Modifier = Modifier
) {
    var polizaId by remember { mutableStateOf(polizas.firstOrNull()?.polizaId.orEmpty()) }
    var fecha by remember { mutableStateOf("") }
    var hora by remember { mutableStateOf("") }
    var lugar by remember { mutableStateOf("") }
    var descripcion by remember { mutableStateOf("") }
    var estimacion by remember { mutableStateOf("") }
    var intentado by remember { mutableStateOf(false) }
    var mostrarFecha by remember { mutableStateOf(false) }
    var mostrarHora by remember { mutableStateOf(false) }

    val puedeEnviar = esFormularioSiniestroValido(polizaId, fecha, hora, lugar, descripcion, estimacion)

    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
        Column(modifier = Modifier.fillMaxSize()) {
            Encabezado(titulo = "Reportar siniestro", onVolver = onVolver)
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 24.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                if (error != null) {
                    Text(text = error, style = MaterialTheme.typography.bodyMedium, color = Atencion)
                }

                if (polizas.isNotEmpty()) {
                    SelectorPoliza(
                        polizas = polizas,
                        seleccionada = polizaId,
                        onSeleccionar = { polizaId = it },
                        error = if (intentado) errorPolizaSiniestro(polizaId) else null
                    )
                } else {
                    SolventaTextField(
                        value = polizaId,
                        onValueChange = { polizaId = it },
                        label = "Póliza",
                        placeholder = "Número o identificador de la póliza",
                        error = if (intentado) errorPolizaSiniestro(polizaId) else null
                    )
                }

                CampoSeleccionable(
                    label = "Fecha del evento",
                    valor = if (fecha.isBlank()) "Selecciona la fecha" else Formatos.fecha(fecha),
                    placeholderActivo = fecha.isNotBlank(),
                    onClick = { mostrarFecha = true },
                    error = if (intentado) errorFechaSiniestro(fecha) else null,
                    icono = Icons.Filled.CalendarMonth
                )
                CampoSeleccionable(
                    label = "Hora del evento",
                    valor = if (hora.isBlank()) "Selecciona la hora" else hora,
                    placeholderActivo = hora.isNotBlank(),
                    onClick = { mostrarHora = true },
                    error = if (intentado) errorHoraSiniestro(hora) else null,
                    icono = Icons.Filled.Schedule
                )
                SolventaTextField(
                    value = lugar,
                    onValueChange = { lugar = it },
                    label = "Lugar",
                    placeholder = "¿Dónde ocurrió?",
                    error = if (intentado) errorLugarSiniestro(lugar) else null
                )
                SolventaTextField(
                    value = descripcion,
                    onValueChange = { descripcion = it },
                    label = "Descripción",
                    placeholder = "Cuéntanos qué pasó",
                    singleLine = false,
                    minLines = 5,
                    error = if (intentado) errorDescripcionSiniestro(descripcion) else null
                )
                SolventaTextField(
                    value = estimacion,
                    onValueChange = { estimacion = it },
                    label = "Estimación del daño (COP)",
                    placeholder = "Ej. 850000",
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    error = if (intentado) errorEstimacionSiniestro(estimacion) else null
                )

                Spacer(modifier = Modifier.size(4.dp))
                SolventaPrimaryButton(
                    text = "Registrar siniestro",
                    onClick = {
                        intentado = true
                        if (puedeEnviar) {
                            onRegistrar(
                                polizaId.trim(),
                                fecha.trim(),
                                hora.trim(),
                                lugar.trim(),
                                descripcion.trim(),
                                normalizarEstimacion(estimacion)
                            )
                        }
                    },
                    enabled = !registrando,
                    isLoading = registrando
                )
                Spacer(modifier = Modifier.size(24.dp))
            }
        }
    }

    if (mostrarFecha) {
        SelectorFecha(
            onConfirmar = { iso ->
                fecha = iso
                mostrarFecha = false
            },
            onCancelar = { mostrarFecha = false }
        )
    }
    if (mostrarHora) {
        SelectorHora(
            onConfirmar = { hhmm ->
                hora = hhmm
                mostrarHora = false
            },
            onCancelar = { mostrarHora = false }
        )
    }
}

/** Campo de solo lectura que abre un selector al tocarlo (fecha/hora). */
@Composable
private fun CampoSeleccionable(
    label: String,
    valor: String,
    placeholderActivo: Boolean,
    onClick: () -> Unit,
    error: String?,
    icono: androidx.compose.ui.graphics.vector.ImageVector
) {
    Column {
        Surface(
            shape = RoundedCornerShape(16.dp),
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp)
                .clickable(onClick = onClick)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = label.uppercase(),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                    )
                    Text(
                        text = valor,
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (placeholderActivo) {
                            MaterialTheme.colorScheme.onSurface
                        } else {
                            MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)
                        }
                    )
                }
                Icon(icono, contentDescription = null)
            }
        }
        if (error != null) {
            Text(
                text = error,
                style = MaterialTheme.typography.labelMedium,
                color = Atencion,
                modifier = Modifier.padding(start = 16.dp, top = 4.dp)
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SelectorFecha(onConfirmar: (String) -> Unit, onCancelar: () -> Unit) {
    // Por defecto hoy; no se permiten fechas futuras (el evento ya ocurrió).
    val hoyMillis = remember { System.currentTimeMillis() }
    val estado = rememberDatePickerState(
        initialSelectedDateMillis = hoyMillis,
        selectableDates = object : SelectableDates {
            override fun isSelectableDate(utcTimeMillis: Long): Boolean =
                utcTimeMillis <= hoyMillis
        }
    )
    DatePickerDialog(
        onDismissRequest = onCancelar,
        confirmButton = {
            TextButton(onClick = {
                val millis = estado.selectedDateMillis
                if (millis != null) onConfirmar(isoDesdeMillisUtc(millis)) else onCancelar()
            }) { Text("Aceptar") }
        },
        dismissButton = { TextButton(onClick = onCancelar) { Text("Cancelar") } }
    ) {
        DatePicker(state = estado)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SelectorHora(onConfirmar: (String) -> Unit, onCancelar: () -> Unit) {
    val ahora = remember { Calendar.getInstance() }
    val estado = rememberTimePickerState(
        initialHour = ahora.get(Calendar.HOUR_OF_DAY),
        initialMinute = ahora.get(Calendar.MINUTE),
        is24Hour = true
    )
    AlertDialog(
        onDismissRequest = onCancelar,
        confirmButton = {
            TextButton(onClick = {
                val hh = estado.hour.toString().padStart(2, '0')
                val mm = estado.minute.toString().padStart(2, '0')
                onConfirmar("$hh:$mm")
            }) { Text("Aceptar") }
        },
        dismissButton = { TextButton(onClick = onCancelar) { Text("Cancelar") } },
        text = {
            Column(horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally) {
                TimePicker(state = estado)
            }
        }
    )
}

/** Convierte los millis UTC del DatePicker a "AAAA-MM-DD" (día calendario, zona UTC). */
private fun isoDesdeMillisUtc(millis: Long): String {
    val cal = Calendar.getInstance(java.util.TimeZone.getTimeZone("UTC")).apply {
        timeInMillis = millis
    }
    val anio = cal.get(Calendar.YEAR)
    val mes = (cal.get(Calendar.MONTH) + 1).toString().padStart(2, '0')
    val dia = cal.get(Calendar.DAY_OF_MONTH).toString().padStart(2, '0')
    return "$anio-$mes-$dia"
}

@Composable
private fun SelectorPoliza(
    polizas: List<PolizaElegible>,
    seleccionada: String,
    onSeleccionar: (String) -> Unit,
    error: String?
) {
    var abierto by remember { mutableStateOf(false) }
    val etiqueta = polizas.firstOrNull { it.polizaId == seleccionada }?.etiqueta
        ?: "Selecciona una póliza"
    Column {
        Surface(
            shape = RoundedCornerShape(16.dp),
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp)
                .clickable { abierto = true }
        ) {
            Row(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
            ) {
                Text(
                    text = etiqueta,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Icon(Icons.Filled.ArrowDropDown, contentDescription = "Elegir póliza")
            }
        }
        DropdownMenu(expanded = abierto, onDismissRequest = { abierto = false }) {
            polizas.forEach { poliza ->
                DropdownMenuItem(
                    text = { Text(poliza.etiqueta) },
                    onClick = {
                        onSeleccionar(poliza.polizaId)
                        abierto = false
                    }
                )
            }
        }
        if (error != null) {
            Text(
                text = error,
                style = MaterialTheme.typography.labelMedium,
                color = Atencion,
                modifier = Modifier.padding(start = 16.dp, top = 4.dp)
            )
        }
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun ClaimFormScreenPreview() {
    SolventaTheme {
        ClaimFormScreen(
            polizas = listOf(
                PolizaElegible("DEMO-04", "Seguro paramétrico · SOL-PM-04"),
                PolizaElegible("DEMO-01", "Seguro de viaje · SOL-VJ-01")
            ),
            registrando = false,
            error = null,
            onRegistrar = { _, _, _, _, _, _ -> },
            onVolver = {}
        )
    }
}
