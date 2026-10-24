package com.example.solventa.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.outlined.AccountBalance
import androidx.compose.material.icons.outlined.CreditCard
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuAnchorType
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.rememberVectorPainter
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.pagos.MetodoPago
import com.example.solventa.domain.pagos.SolicitudPago
import com.example.solventa.ui.components.SolventaBottomNavigation
import com.example.solventa.ui.components.SolventaNoticePill
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaSecondaryButton
import com.example.solventa.ui.components.SolventaTextField
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.Noche
import java.math.BigDecimal
import java.text.NumberFormat
import java.util.Locale

/** Bancos simulados para el flujo PSE (desarrollo). */
private val BANCOS_PSE = listOf(
    "1007" to "Bancolombia",
    "1051" to "Davivienda",
    "1001" to "Banco de Bogotá",
    "1023" to "Banco de Occidente",
    "1062" to "Banco Falabella",
    "1151" to "Nequi"
)

/** Pantalla de recaudo de la prima (HU13 / HU23): tarjeta o PSE. */
@Composable
fun PaymentScreen(
    cotizacionId: String,
    monto: BigDecimal,
    moneda: String,
    procesando: Boolean,
    error: String?,
    onVolver: () -> Unit,
    onPagar: (SolicitudPago) -> Unit,
    modifier: Modifier = Modifier,
    onInicio: () -> Unit = {},
    urlRetorno: String? = null
) {
    var metodo by rememberSaveable { mutableStateOf(MetodoPago.TARJETA) }
    var numeroTarjeta by rememberSaveable { mutableStateOf("") }
    var vencimiento by rememberSaveable { mutableStateOf("") }
    var cvv by rememberSaveable { mutableStateOf("") }
    var codigoBanco by rememberSaveable { mutableStateOf("") }
    var mostrarErrores by rememberSaveable { mutableStateOf(false) }

    val tarjetaCompleta = numeroTarjeta.filter(Char::isDigit).length >= 13 &&
        vencimiento.length >= 4 && cvv.length >= 3
    val pseCompleto = codigoBanco.isNotBlank()
    val puedePagar = if (metodo == MetodoPago.TARJETA) tarjetaCompleta else pseCompleto

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        bottomBar = { SolventaBottomNavigation(onInicio = onInicio, onPolizas = null) }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
        ) {
            EncabezadoPago(onVolver = onVolver)
            Column(
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 18.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Text(
                    text = "PAGO DE LA PRIMA",
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                    color = Navegacion
                )
                TarjetaTotal(monto, moneda)

                Text(
                    text = "¿Cómo quieres pagar?",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.onSurface
                )
                OpcionMetodo(
                    seleccionado = metodo == MetodoPago.TARJETA,
                    titulo = "Tarjeta de crédito o débito",
                    icono = rememberVectorPainter(Icons.Outlined.CreditCard),
                    onClick = { metodo = MetodoPago.TARJETA }
                )
                OpcionMetodo(
                    seleccionado = metodo == MetodoPago.PSE,
                    titulo = "PSE (débito bancario)",
                    icono = rememberVectorPainter(Icons.Outlined.AccountBalance),
                    onClick = { metodo = MetodoPago.PSE }
                )

                if (metodo == MetodoPago.TARJETA) {
                    SolventaTextField(
                        value = numeroTarjeta,
                        onValueChange = { numeroTarjeta = formatearNumeroTarjeta(it) },
                        label = "Número de tarjeta",
                        placeholder = "4111 1111 1111 1111",
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        error = if (mostrarErrores && !tarjetaCompleta) "Revisa los datos de la tarjeta." else null
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Column(modifier = Modifier.weight(1f)) {
                            SolventaTextField(
                                value = vencimiento,
                                onValueChange = { vencimiento = formatearVencimiento(it) },
                                label = "Vencimiento",
                                placeholder = "MM/AA",
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                            )
                        }
                        Column(modifier = Modifier.weight(1f)) {
                            SolventaTextField(
                                value = cvv,
                                onValueChange = { cvv = it.filter(Char::isDigit).take(4) },
                                label = "CVV",
                                placeholder = "123",
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                            )
                        }
                    }
                    SolventaNoticePill(
                        text = "Tus datos se tokenizan en el dispositivo; nunca enviamos el número de la tarjeta.",
                        icon = rememberVectorPainter(Icons.Outlined.Lock)
                    )
                } else {
                    CampoBancoPse(
                        codigoBanco = codigoBanco,
                        onSeleccionar = { codigoBanco = it },
                        error = if (mostrarErrores && !pseCompleto) "Selecciona tu banco." else null
                    )
                }

                if (error != null) {
                    Text(
                        text = error,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.error
                    )
                }

                SolventaPrimaryButton(
                    text = "Pagar prima",
                    isLoading = procesando,
                    onClick = {
                        if (!puedePagar) {
                            mostrarErrores = true
                            return@SolventaPrimaryButton
                        }
                        onPagar(
                            if (metodo == MetodoPago.TARJETA) {
                                SolicitudPago(
                                    cotizacionId = cotizacionId,
                                    metodo = MetodoPago.TARJETA,
                                    tokenTarjeta = tokenizarTarjeta(numeroTarjeta)
                                )
                            } else {
                                SolicitudPago(
                                    cotizacionId = cotizacionId,
                                    metodo = MetodoPago.PSE,
                                    codigoBanco = codigoBanco,
                                    urlRetorno = urlRetorno
                                )
                            }
                        )
                    }
                )
                SolventaSecondaryButton(text = "Volver", onClick = onVolver)
            }
        }
    }
}

@Composable
private fun TarjetaTotal(monto: BigDecimal, moneda: String) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = Noche,
        shape = RoundedCornerShape(18.dp)
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                text = "TOTAL A PAGAR",
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                color = Color.White.copy(alpha = 0.7f)
            )
            Text(
                text = formatearMonedaPago(monto, moneda),
                style = MaterialTheme.typography.headlineLarge,
                color = Color.White
            )
        }
    }
}

@Composable
private fun OpcionMetodo(
    seleccionado: Boolean,
    titulo: String,
    icono: androidx.compose.ui.graphics.painter.Painter,
    onClick: () -> Unit
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .selectable(selected = seleccionado, onClick = onClick),
        color = if (seleccionado) Navegacion.copy(alpha = 0.08f) else MaterialTheme.colorScheme.surface,
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(
            1.dp,
            if (seleccionado) Navegacion else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f)
        )
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            RadioButton(selected = seleccionado, onClick = onClick)
            Icon(painter = icono, contentDescription = null, tint = Navegacion, modifier = Modifier.size(22.dp))
            Spacer(modifier = Modifier.size(2.dp))
            Text(
                text = titulo,
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CampoBancoPse(
    codigoBanco: String,
    onSeleccionar: (String) -> Unit,
    error: String?
) {
    var expandido by remember { mutableStateOf(false) }
    val nombre = BANCOS_PSE.firstOrNull { it.first == codigoBanco }?.second.orEmpty()

    ExposedDropdownMenuBox(expanded = expandido, onExpandedChange = { expandido = it }) {
        SolventaTextField(
            value = nombre,
            onValueChange = {},
            label = "Banco",
            placeholder = "Selecciona tu banco",
            readOnly = true,
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expandido) },
            error = error,
            modifier = Modifier.menuAnchor(ExposedDropdownMenuAnchorType.PrimaryNotEditable)
        )
        ExposedDropdownMenu(expanded = expandido, onDismissRequest = { expandido = false }) {
            BANCOS_PSE.forEach { (codigo, etiqueta) ->
                DropdownMenuItem(
                    text = { Text(etiqueta) },
                    onClick = {
                        onSeleccionar(codigo)
                        expandido = false
                    }
                )
            }
        }
    }
}

@Composable
private fun EncabezadoPago(onVolver: () -> Unit) {
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
            text = "Pagar la prima",
            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
            color = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.weight(1f)
        )
    }
}

internal fun formatearNumeroTarjeta(valor: String): String {
    val digitos = valor.filter(Char::isDigit).take(16)
    return digitos.chunked(4).joinToString(" ")
}

internal fun formatearVencimiento(valor: String): String {
    val digitos = valor.filter(Char::isDigit).take(4)
    return if (digitos.length <= 2) digitos else "${digitos.take(2)}/${digitos.drop(2)}"
}

/**
 * Simula la tokenización del SDK de la pasarela: el número de tarjeta no sale del dispositivo.
 * Para desarrollo, una tarjeta terminada en 0 fuerza un rechazo (fondos insuficientes).
 */
internal fun tokenizarTarjeta(numero: String): String {
    val digitos = numero.filter(Char::isDigit)
    val prefijo = if (digitos.endsWith("0")) "tok_rechazado" else "tok_visa"
    return "${prefijo}_${java.util.UUID.randomUUID().toString().replace("-", "").take(16)}"
}

private fun formatearMonedaPago(valor: BigDecimal, moneda: String): String {
    val formato = NumberFormat.getNumberInstance(Locale.forLanguageTag("es-CO")).apply {
        minimumFractionDigits = if (valor.stripTrailingZeros().scale() > 0) 2 else 0
        maximumFractionDigits = 2
    }
    return "$${formato.format(valor)} $moneda"
}
