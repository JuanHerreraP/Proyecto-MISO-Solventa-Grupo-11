package com.example.solventa.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.outlined.KeyboardArrowDown
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuAnchorType
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.rememberVectorPainter
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.cotizaciones.CampoCotizacion
import com.example.solventa.domain.cotizaciones.CatalogoCotizaciones
import com.example.solventa.domain.cotizaciones.DefinicionRamoCotizacion
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.example.solventa.domain.cotizaciones.TipoCampoCotizacion
import com.example.solventa.ui.components.SolventaBottomNavigation
import com.example.solventa.ui.components.SolventaNoticePill
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaTextField
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.SolventaTheme
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/** Formulario único que renderiza los campos correspondientes al ramo seleccionado. */
@Composable
fun QuoteFormScreen(
    definicion: DefinicionRamoCotizacion,
    onVolver: () -> Unit,
    onCalcular: (Map<String, String>) -> Unit,
    modifier: Modifier = Modifier,
    onInicio: () -> Unit = {},
    onVerBilletera: (() -> Unit)? = null,
    cargando: Boolean = false,
    errorRemoto: String? = null
) {
    var valores by rememberSaveable(definicion.ramo) {
        mutableStateOf(emptyMap<String, String>())
    }
    var mostrarErrores by rememberSaveable(definicion.ramo) { mutableStateOf(false) }

    fun actualizar(codigo: String, valor: String) {
        valores = valores + (codigo to valor)
        if (codigo == "tipo_evento") {
            valores = when (valor) {
                "RETRASO_VUELO" -> valores - "ubicacion"
                "EVENTO_CLIMATICO" -> valores - "numero_vuelo"
                else -> valores
            }
        }
    }

    val camposVisibles = definicion.campos.filter { campoVisible(it, valores) }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        bottomBar = {
            SolventaBottomNavigation(onInicio = onInicio, onPolizas = onVerBilletera)
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
        ) {
            EncabezadoFormulario(
                titulo = tituloRamo(definicion.ramo),
                onVolver = onVolver
            )
            Column(
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 18.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                Text(
                    text = "COTIZACIÓN",
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                    color = Navegacion
                )
                Text(
                    text = definicion.tituloFormulario,
                    style = MaterialTheme.typography.headlineMedium,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Text(
                    text = definicion.descripcionFormulario,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
                )

                camposVisibles.forEach { campo ->
                    CampoDinamico(
                        campo = campo,
                        valor = valores[campo.codigo].orEmpty(),
                        error = if (
                            mostrarErrores &&
                            campoRequerido(campo, valores) &&
                            valores[campo.codigo].isNullOrBlank()
                        ) {
                            "Este campo es obligatorio."
                        } else {
                            null
                        },
                        onValueChange = { actualizar(campo.codigo, it) }
                    )
                }

                SolventaNoticePill(
                    text = "Usaremos únicamente los datos financieros que autorizaste para personalizar el precio.",
                    icon = rememberVectorPainter(Icons.Outlined.Shield)
                )

                if (errorRemoto != null) {
                    Text(
                        text = errorRemoto,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.error
                    )
                }

                SolventaPrimaryButton(
                    text = "Calcular cotización",
                    isLoading = cargando,
                    onClick = {
                        val incompleto = camposVisibles.any {
                            campoRequerido(it, valores) && valores[it.codigo].isNullOrBlank()
                        }
                        mostrarErrores = incompleto
                        if (!incompleto) onCalcular(valores)
                    }
                )
            }
        }
    }
}

@Composable
private fun CampoDinamico(
    campo: CampoCotizacion,
    valor: String,
    error: String?,
    onValueChange: (String) -> Unit
) {
    when (campo.tipo) {
        TipoCampoCotizacion.OPCION -> CampoOpcion(campo, valor, error, onValueChange)
        TipoCampoCotizacion.BOOLEANO -> CampoBooleano(campo, valor, error, onValueChange)
        TipoCampoCotizacion.FECHA -> CampoFecha(campo, valor, error, onValueChange)
        else -> SolventaTextField(
            value = valor,
            onValueChange = onValueChange,
            label = etiquetaCampo(campo),
            placeholder = placeholderCampo(campo),
            keyboardOptions = KeyboardOptions(keyboardType = tecladoCampo(campo.tipo)),
            error = error
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CampoFecha(
    campo: CampoCotizacion,
    valor: String,
    error: String?,
    onValueChange: (String) -> Unit
) {
    var mostrarCalendario by remember { mutableStateOf(false) }
    val estadoCalendario = androidx.compose.material3.rememberDatePickerState(
        initialSelectedDateMillis = valor.aMilisegundosUtc()
    )

    Box(modifier = Modifier.fillMaxWidth()) {
        SolventaTextField(
            value = valor,
            onValueChange = {},
            label = etiquetaCampo(campo),
            placeholder = "AAAA-MM-DD",
            readOnly = true,
            trailingIcon = {
                Icon(
                    imageVector = Icons.Outlined.CalendarMonth,
                    contentDescription = "Abrir calendario"
                )
            },
            error = error
        )
        Box(
            modifier = Modifier
                .matchParentSize()
                .testTag("campo_${campo.codigo}")
                .clickable { mostrarCalendario = true }
        )
    }

    if (mostrarCalendario) {
        DatePickerDialog(
            onDismissRequest = { mostrarCalendario = false },
            confirmButton = {
                TextButton(
                    enabled = estadoCalendario.selectedDateMillis != null,
                    onClick = {
                        estadoCalendario.selectedDateMillis?.let { onValueChange(it.aFechaApi()) }
                        mostrarCalendario = false
                    }
                ) {
                    Text("Aceptar")
                }
            },
            dismissButton = {
                TextButton(onClick = { mostrarCalendario = false }) {
                    Text("Cancelar")
                }
            }
        ) {
            DatePicker(
                state = estadoCalendario,
                title = {
                    Text(
                        text = "Selecciona una fecha",
                        modifier = Modifier.padding(start = 24.dp, top = 16.dp)
                    )
                }
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CampoOpcion(
    campo: CampoCotizacion,
    valor: String,
    error: String?,
    onValueChange: (String) -> Unit
) {
    var expandido by remember { mutableStateOf(false) }

    ExposedDropdownMenuBox(expanded = expandido, onExpandedChange = { expandido = it }) {
        SolventaTextField(
            value = etiquetaOpcion(valor),
            onValueChange = {},
            label = etiquetaCampo(campo),
            placeholder = "Selecciona una opción",
            readOnly = true,
            trailingIcon = {
                ExposedDropdownMenuDefaults.TrailingIcon(expanded = expandido)
            },
            error = error,
            modifier = Modifier
                .menuAnchor(ExposedDropdownMenuAnchorType.PrimaryNotEditable)
                .testTag("campo_${campo.codigo}")
        )
        ExposedDropdownMenu(expanded = expandido, onDismissRequest = { expandido = false }) {
            campo.opciones.forEach { opcion ->
                DropdownMenuItem(
                    text = { Text(etiquetaOpcion(opcion)) },
                    modifier = Modifier.testTag("opcion_${campo.codigo}_$opcion"),
                    onClick = {
                        onValueChange(opcion)
                        expandido = false
                    }
                )
            }
        }
    }
}

@Composable
private fun CampoBooleano(
    campo: CampoCotizacion,
    valor: String,
    error: String?,
    onValueChange: (String) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(
            text = etiquetaCampo(campo).uppercase(),
            style = MaterialTheme.typography.labelMedium,
            color = if (error == null) {
                MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
            } else {
                MaterialTheme.colorScheme.error
            }
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            FilterChip(
                selected = valor == "true",
                onClick = { onValueChange("true") },
                label = { Text("Sí") },
                modifier = Modifier.weight(1f)
            )
            FilterChip(
                selected = valor == "false",
                onClick = { onValueChange("false") },
                label = { Text("No") },
                modifier = Modifier.weight(1f)
            )
        }
        if (error != null) {
            Text(error, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.error)
        }
    }
}

@Composable
private fun EncabezadoFormulario(titulo: String, onVolver: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        IconButton(onClick = onVolver) {
            Icon(
                imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                contentDescription = "Volver",
                tint = MaterialTheme.colorScheme.onSurface
            )
        }
        Text(
            text = titulo,
            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
            color = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.weight(1f)
        )
        Text(
            text = "PASO 2 DE 3",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f),
            modifier = Modifier.padding(end = 12.dp)
        )
    }
}

private fun campoVisible(campo: CampoCotizacion, valores: Map<String, String>): Boolean =
    when (campo.codigo) {
        "numero_vuelo" -> valores["tipo_evento"] == "RETRASO_VUELO"
        "ubicacion" -> valores["tipo_evento"] == "EVENTO_CLIMATICO"
        else -> true
    }

private fun campoRequerido(campo: CampoCotizacion, valores: Map<String, String>): Boolean =
    campo.requerido ||
        (campo.codigo == "numero_vuelo" && valores["tipo_evento"] == "RETRASO_VUELO") ||
        (campo.codigo == "ubicacion" && valores["tipo_evento"] == "EVENTO_CLIMATICO")

private fun etiquetaCampo(campo: CampoCotizacion): String =
    if (campo.requerido || campo.codigo in setOf("numero_vuelo", "ubicacion")) {
        campo.etiqueta
    } else {
        "${campo.etiqueta} (Opcional)"
    }

private fun placeholderCampo(campo: CampoCotizacion): String = when (campo.tipo) {
    TipoCampoCotizacion.FECHA -> "AAAA-MM-DD"
    TipoCampoCotizacion.ENTERO -> "Ingresa un número"
    TipoCampoCotizacion.DECIMAL -> if (campo.unidad == "COP") "$ 0 COP" else "0"
    else -> campo.descripcion
}

private fun tecladoCampo(tipo: TipoCampoCotizacion): KeyboardType = when (tipo) {
    TipoCampoCotizacion.ENTERO -> KeyboardType.Number
    TipoCampoCotizacion.DECIMAL -> KeyboardType.Decimal
    TipoCampoCotizacion.FECHA -> KeyboardType.Number
    else -> KeyboardType.Text
}

private fun etiquetaOpcion(opcion: String): String = opcion
    .lowercase()
    .replace('_', ' ')
    .replaceFirstChar { it.titlecase() }

private fun String.aMilisegundosUtc(): Long? = takeIf(String::isNotBlank)?.let { fecha ->
    formatoFechaApi().runCatching { parse(fecha)?.time }.getOrNull()
}

private fun Long.aFechaApi(): String = formatoFechaApi().format(Date(this))

private fun formatoFechaApi() = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).apply {
    isLenient = false
    timeZone = TimeZone.getTimeZone("UTC")
}

private fun tituloRamo(ramo: RamoCotizacion): String = when (ramo) {
    RamoCotizacion.VIAJE -> "Seguro de viaje"
    RamoCotizacion.DISPOSITIVOS -> "Protección de dispositivos"
    RamoCotizacion.VIDA -> "Seguro de vida"
    RamoCotizacion.PARAMETRICO -> "Seguro paramétrico"
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
private fun QuoteFormScreenPreview() {
    SolventaTheme {
        QuoteFormScreen(
            definicion = CatalogoCotizaciones.definicion(RamoCotizacion.VIAJE),
            onVolver = {},
            onCalcular = {}
        )
    }
}
