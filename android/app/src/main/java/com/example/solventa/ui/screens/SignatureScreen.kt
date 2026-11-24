package com.example.solventa.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
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
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.example.solventa.R
import com.example.solventa.domain.firmas.EstadoFirma
import com.example.solventa.domain.firmas.MensajesFirma
import com.example.solventa.domain.firmas.ProcesoFirma
import com.example.solventa.i18n.Idioma
import com.example.solventa.i18n.tr
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaSecondaryButton
import com.example.solventa.ui.theme.Navegacion
import java.math.BigDecimal
import java.text.NumberFormat

/** Revisión contractual, OTP y emisión de póliza desde Android. */
@Composable
fun SignatureScreen(
    estado: EstadoFirma,
    onSolicitarCodigo: () -> Unit,
    onFirmar: (String) -> Unit,
    onVolver: () -> Unit,
    onVerPoliza: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val proceso = estado.proceso
    var codigo by rememberSaveable { mutableStateOf("") }
    var acepta by rememberSaveable { mutableStateOf(false) }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets(0, 0, 0, 0)
    ) { padding ->
        when {
            estado.cargando && proceso == null -> CargandoContrato(Modifier.padding(padding))
            proceso == null -> ErrorFirma(
                error = textoErrorFirma(estado.error),
                onVolver = onVolver,
                modifier = Modifier.padding(padding)
            )
            proceso.polizaId != null -> FirmaCompletada(
                onVerPoliza = { onVerPoliza(proceso.polizaId) },
                modifier = Modifier.padding(padding)
            )
            else -> ContenidoFirma(
                proceso = proceso,
                codigo = codigo,
                acepta = acepta,
                estado = estado,
                onCodigo = { codigo = it.filter(Char::isDigit).take(6) },
                onAcepta = { acepta = it },
                onSolicitarCodigo = onSolicitarCodigo,
                onFirmar = { onFirmar(codigo) },
                onVolver = onVolver,
                modifier = Modifier.padding(padding)
            )
        }
    }
}

@Composable
private fun CargandoContrato(modifier: Modifier) {
    Column(
        modifier = modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        CircularProgressIndicator(color = Navegacion)
        Text(tr(R.string.signature_cargando_tu_contrato), modifier = Modifier.padding(top = 16.dp))
    }
}

@Composable
private fun ErrorFirma(error: String, onVolver: () -> Unit, modifier: Modifier) {
    Column(
        modifier = modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(Icons.Outlined.Description, null, tint = Navegacion, modifier = Modifier.size(48.dp))
        Text(error, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(vertical = 20.dp))
        SolventaPrimaryButton(text = tr(R.string.biometrical_login_volver), onClick = onVolver)
    }
}

@Composable
private fun ContenidoFirma(
    proceso: ProcesoFirma,
    codigo: String,
    acepta: Boolean,
    estado: EstadoFirma,
    onCodigo: (String) -> Unit,
    onAcepta: (Boolean) -> Unit,
    onSolicitarCodigo: () -> Unit,
    onFirmar: () -> Unit,
    onVolver: () -> Unit,
    modifier: Modifier
) {
    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(tr(R.string.signature_firma_electronica), style = MaterialTheme.typography.headlineMedium)
        Text(
            tr(R.string.signature_revisa_las_condiciones),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
        )
        ResumenContrato(proceso)
        proceso.contrato.clausulas.take(3).takeIf { it.isNotEmpty() }?.let { clausulas ->
            SeccionContrato(tr(R.string.signature_condiciones)) {
                clausulas.forEach { TextoContrato("• $it") }
            }
        }
        proceso.contrato.exclusionesPrincipales.takeIf { it.isNotEmpty() }?.let { exclusiones ->
            SeccionContrato(tr(R.string.certificate_exclusiones_principales)) {
                exclusiones.forEach { TextoContrato("• $it") }
            }
        }
        Surface(
            color = Navegacion.copy(alpha = 0.08f),
            shape = RoundedCornerShape(14.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                modifier = Modifier.padding(14.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(Icons.Outlined.Lock, null, tint = Navegacion)
                Text(tr(R.string.signature_huella_documento, proceso.huellaDocumento.take(12)))
            }
        }
        if (proceso.otpDestino == null) {
            SolventaPrimaryButton(
                text = tr(
                    if (estado.enviandoCodigo) R.string.signature_enviando_codigo else R.string.signature_enviar_codigo_sms
                ),
                onClick = onSolicitarCodigo,
                enabled = !estado.enviandoCodigo
            )
        } else {
            Text(
                tr(R.string.signature_codigo_enviado_a, proceso.otpDestino),
                style = MaterialTheme.typography.bodyMedium,
                color = Color(0xFF1B8A4A)
            )
            OutlinedTextField(
                value = codigo,
                onValueChange = onCodigo,
                label = { Text(tr(R.string.signature_codigo_seis_digitos)) },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(checked = acepta, onCheckedChange = onAcepta)
                Text(tr(R.string.signature_acepto_condiciones), style = MaterialTheme.typography.bodySmall)
            }
            SolventaPrimaryButton(
                text = tr(if (estado.firmando) R.string.signature_firmando else R.string.signature_firmar_y_emitir),
                onClick = onFirmar,
                enabled = codigo.length == 6 && acepta && !estado.firmando
            )
            SolventaSecondaryButton(
                text = tr(if (estado.enviandoCodigo) R.string.signature_enviando_codigo else R.string.signature_reenviar_codigo),
                onClick = onSolicitarCodigo,
                enabled = !estado.enviandoCodigo && !estado.firmando
            )
        }
        estado.error?.let { Text(textoErrorFirma(it), color = MaterialTheme.colorScheme.error) }
        SolventaSecondaryButton(
            text = tr(R.string.biometrical_login_volver),
            onClick = onVolver,
            enabled = !estado.firmando
        )
    }
}

@Composable
private fun ResumenContrato(proceso: ProcesoFirma) {
    SeccionContrato(tr(R.string.signature_contrato_de, proceso.contrato.nombreRamo)) {
        TextoContrato(proceso.contrato.coberturaPrincipal)
        TextoContrato(tr(R.string.signature_suma_asegurada, moneda(proceso.contrato.sumaAsegurada, proceso.contrato.moneda)))
        TextoContrato(tr(R.string.signature_prima_pagada, moneda(proceso.contrato.primaTotal, proceso.contrato.moneda)))
    }
}

@Composable
private fun SeccionContrato(titulo: String, contenido: @Composable () -> Unit) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surfaceContainer,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(titulo, style = MaterialTheme.typography.titleMedium)
            contenido()
        }
    }
}

@Composable
private fun TextoContrato(texto: String) {
    Text(texto, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.75f))
}

@Composable
private fun FirmaCompletada(onVerPoliza: () -> Unit, modifier: Modifier) {
    Column(
        modifier = modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(Icons.Outlined.CheckCircle, null, tint = Color(0xFF1B8A4A), modifier = Modifier.size(64.dp))
        Text(
            tr(R.string.signature_contrato_firmado),
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.padding(top = 20.dp)
        )
        Text(
            tr(R.string.signature_poliza_emitida),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            modifier = Modifier.padding(vertical = 10.dp)
        )
        SolventaPrimaryButton(text = tr(R.string.signature_ver_poliza), onClick = onVerPoliza)
    }
}

private fun textoErrorFirma(error: String?): String = when (error) {
    MensajesFirma.SIN_CONEXION -> tr(R.string.signature_error_sin_conexion)
    MensajesFirma.CODIGO_INVALIDO -> tr(R.string.signature_error_codigo_invalido)
    MensajesFirma.SESION_VENCIDA -> tr(R.string.signature_error_sesion_vencida)
    MensajesFirma.CONTRATO_NO_DISPONIBLE -> tr(R.string.signature_error_contrato_no_disponible)
    else -> tr(R.string.signature_error_generico)
}

private fun moneda(valor: BigDecimal, codigo: String): String {
    val formato = NumberFormat.getNumberInstance(Idioma.locale())
    return "$${formato.format(valor)} $codigo"
}
