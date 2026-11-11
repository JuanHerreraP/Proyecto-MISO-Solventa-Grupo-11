package com.example.solventa.ui.screens

import androidx.compose.foundation.BorderStroke
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Block
import androidx.compose.material.icons.outlined.ExpandMore
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.WarningAmber
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.polizas.BloqueoCancelacion
import com.example.solventa.domain.polizas.Formatos
import com.example.solventa.domain.polizas.MotivoCancelacion
import com.example.solventa.domain.polizas.PropuestaCancelacion
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.SolventaTheme

private val Borde = Color(0xFFE2E8F0)
private val AvisoFondo = Color(0xFFFFEEDD)
private val AvisoTexto = Color(0xFF9A4A06)
private val RojoCancelar = Color(0xFFC62828)
private val FondoCancelar = Color(0xFFFDECEC)
private val BordeCancelar = Color(0xFFF5C6C6)

/** Confirmación explícita de la cancelación: consecuencias, motivo y saldo a favor (HU22). */
@Composable
fun CancelScreen(
    propuesta: PropuestaCancelacion?,
    cargando: Boolean,
    error: String?,
    cancelando: Boolean,
    onConfirmar: (motivo: String) -> Unit,
    onReintentar: () -> Unit,
    onConservar: () -> Unit,
    onVolver: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
        Column(modifier = Modifier.fillMaxSize()) {
            Encabezado(titulo = "Pólizas", onVolver = onVolver)

            when {
                propuesta == null && cargando -> Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(
                        color = Navegacion,
                        modifier = Modifier.semantics {
                            contentDescription = "Cargando las condiciones de la cancelación"
                        }
                    )
                }

                propuesta == null -> Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = error ?: "No pudimos cargar la cancelación.",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.size(16.dp))
                    SolventaPrimaryButton(text = "Reintentar", onClick = onReintentar)
                }

                else -> Contenido(
                    propuesta = propuesta,
                    error = error,
                    cancelando = cancelando,
                    onConfirmar = onConfirmar,
                    onConservar = onConservar
                )
            }
        }
    }
}

@Composable
private fun Contenido(
    propuesta: PropuestaCancelacion,
    error: String?,
    cancelando: Boolean,
    onConfirmar: (String) -> Unit,
    onConservar: () -> Unit
) {
    var motivoElegido by rememberSaveable { mutableStateOf(propuesta.motivos.firstOrNull()?.codigo) }
    val motivo = propuesta.motivos.firstOrNull { it.codigo == motivoElegido }
        ?: propuesta.motivos.firstOrNull()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp)
            .padding(bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(
                text = "Confirma tu decisión",
                style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = "La cobertura y los cobros programados terminarán al procesar la cancelación.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
        }

        if (propuesta.cancelable) {
            Aviso(
                "Perderás la protección asociada a la póliza ${propuesta.numeroPoliza}."
            )
            if (motivo != null) {
                SelectorMotivo(
                    motivos = propuesta.motivos,
                    seleccionado = motivo,
                    habilitado = !cancelando,
                    onSeleccionar = { motivoElegido = it.codigo }
                )
            }
            Surface(
                shape = RoundedCornerShape(16.dp),
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    Text(
                        text = "Saldo estimado a favor",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                    )
                    Text(
                        text = "${Formatos.dinero(propuesta.saldoEstimado, propuesta.moneda)} ${propuesta.moneda}",
                        style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }
        } else {
            // No se puede cancelar (p. ej. siniestro en trámite): se explica el motivo.
            Aviso(
                propuesta.bloqueos.ifEmpty {
                    listOf(BloqueoCancelacion("", "No se puede cancelar en este momento."))
                }.joinToString("\n") { it.mensaje }
            )
        }

        if (error != null) {
            Text(
                text = error,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error
            )
        }

        if (propuesta.cancelable && motivo != null) {
            OutlinedButton(
                onClick = { onConfirmar(motivo.codigo) },
                enabled = !cancelando,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, BordeCancelar),
                colors = androidx.compose.material3.ButtonDefaults.outlinedButtonColors(
                    containerColor = FondoCancelar,
                    contentColor = RojoCancelar,
                    disabledContainerColor = FondoCancelar
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp)
            ) {
                if (cancelando) {
                    CircularProgressIndicator(
                        color = RojoCancelar,
                        strokeWidth = 2.dp,
                        modifier = Modifier
                            .size(20.dp)
                            .semantics { contentDescription = "Cancelando la póliza" }
                    )
                } else {
                    ContenidoBoton(Icons.Outlined.Block, "Confirmar cancelación")
                }
            }
        }
        OutlinedButton(
            onClick = onConservar,
            enabled = !cancelando,
            shape = RoundedCornerShape(14.dp),
            border = BorderStroke(1.dp, Borde),
            colors = androidx.compose.material3.ButtonDefaults.outlinedButtonColors(
                contentColor = MaterialTheme.colorScheme.onSurface
            ),
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp)
        ) { ContenidoBoton(Icons.Outlined.Shield, "Conservar mi póliza") }
    }
}

@Composable
private fun ContenidoBoton(icono: ImageVector, texto: String) {
    Icon(imageVector = icono, contentDescription = null, modifier = Modifier.size(20.dp))
    Spacer(modifier = Modifier.size(10.dp))
    Text(text = texto, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
}

@Composable
private fun Aviso(texto: String) {
    Surface(
        shape = RoundedCornerShape(14.dp),
        color = AvisoFondo,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = Icons.Outlined.WarningAmber,
                contentDescription = null,
                tint = AvisoTexto,
                modifier = Modifier.size(22.dp)
            )
            Text(
                text = texto,
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                color = AvisoTexto
            )
        }
    }
}

@Composable
private fun SelectorMotivo(
    motivos: List<MotivoCancelacion>,
    seleccionado: MotivoCancelacion,
    habilitado: Boolean,
    onSeleccionar: (MotivoCancelacion) -> Unit
) {
    var abierto by rememberSaveable { mutableStateOf(false) }
    Box(modifier = Modifier.fillMaxWidth()) {
        Surface(
            shape = RoundedCornerShape(16.dp),
            color = MaterialTheme.colorScheme.surface,
            border = BorderStroke(1.dp, Borde),
            modifier = Modifier
                .fillMaxWidth()
                .clickable(
                    enabled = habilitado,
                    role = Role.DropdownList,
                    onClickLabel = "Elegir el motivo de cancelación"
                ) { abierto = true }
        ) {
            Row(
                modifier = Modifier.padding(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        text = "Motivo de cancelación",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                    )
                    Text(
                        text = seleccionado.etiqueta,
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
                Icon(
                    imageVector = Icons.Outlined.ExpandMore,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                )
            }
        }
        DropdownMenu(expanded = abierto, onDismissRequest = { abierto = false }) {
            motivos.forEach { opcion ->
                DropdownMenuItem(
                    text = { Text(opcion.etiqueta) },
                    onClick = {
                        abierto = false
                        onSeleccionar(opcion)
                    }
                )
            }
        }
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun CancelScreenPreview() {
    SolventaTheme {
        CancelScreen(
            propuesta = PropuestaCancelacion(
                polizaId = "1",
                numeroPoliza = "SV-10482",
                cancelable = true,
                bloqueos = emptyList(),
                saldoEstimado = "24500.00",
                moneda = "COP",
                motivos = listOf(MotivoCancelacion("YA_NO_LA_NECESITO", "Ya no necesito la cobertura"))
            ),
            cargando = false,
            error = null,
            cancelando = false,
            onConfirmar = {},
            onReintentar = {},
            onConservar = {},
            onVolver = {}
        )
    }
}
