package com.example.solventa.ui.screens

import androidx.compose.foundation.BorderStroke
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
import androidx.compose.material.icons.outlined.Autorenew
import androidx.compose.material.icons.outlined.Cancel
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.History
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
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
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.R
import com.example.solventa.domain.polizas.Certificado
import com.example.solventa.domain.polizas.CondicionParametrica
import com.example.solventa.domain.polizas.EstadoPoliza
import com.example.solventa.domain.polizas.Formatos
import com.example.solventa.domain.polizas.HistorialEndosos
import com.example.solventa.ui.components.SolventaCodigoQr
import com.example.solventa.ui.components.SolventaNoticePill
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaSecondaryButton
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.SolventaTheme

private val FondoEncabezado = Color(0xFF0F1B2D)
private val BordeTarjeta = Color(0xFFE2E8F0)
private val RojoCancelar = Color(0xFFC62828)
private val FondoCancelar = Color(0xFFFDECEC)
private val BordeCancelar = Color(0xFFF5C6C6)

/** Detalle contractual de la póliza, certificado e historial de movimientos (HU09). */
@Composable
fun CertificateScreen(
    certificado: Certificado?,
    cargando: Boolean,
    error: String?,
    historial: HistorialEndosos?,
    cargandoHistorial: Boolean,
    errorHistorial: String?,
    descargandoDocumento: Boolean,
    compartiendo: Boolean,
    mensaje: String?,
    onVerDocumento: () -> Unit,
    onCompartir: () -> Unit,
    onReintentar: () -> Unit,
    onVolver: () -> Unit,
    modifier: Modifier = Modifier,
    onRenovar: () -> Unit = {},
    onCancelar: () -> Unit = {}
) {
    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
        Column(modifier = Modifier.fillMaxSize()) {
            Encabezado(titulo = "Pólizas", onVolver = onVolver)

            when {
                certificado == null && cargando -> Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(
                        color = Navegacion,
                        modifier = Modifier.semantics { contentDescription = "Cargando el certificado" }
                    )
                }

                certificado == null -> Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = error ?: "No pudimos cargar el certificado.",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.size(16.dp))
                    SolventaPrimaryButton(text = "Reintentar", onClick = onReintentar)
                }

                else -> Contenido(
                    certificado = certificado,
                    historial = historial,
                    cargandoHistorial = cargandoHistorial,
                    errorHistorial = errorHistorial,
                    descargandoDocumento = descargandoDocumento,
                    compartiendo = compartiendo,
                    mensaje = mensaje,
                    onVerDocumento = onVerDocumento,
                    onCompartir = onCompartir,
                    onRenovar = onRenovar,
                    onCancelar = onCancelar
                )
            }
        }
    }
}

@Composable
private fun Contenido(
    certificado: Certificado,
    historial: HistorialEndosos?,
    cargandoHistorial: Boolean,
    errorHistorial: String?,
    descargandoDocumento: Boolean,
    compartiendo: Boolean,
    mensaje: String?,
    onVerDocumento: () -> Unit,
    onCompartir: () -> Unit,
    onRenovar: () -> Unit,
    onCancelar: () -> Unit
) {
    // Con un aviso pendiente (p. ej. no se pudo compartir) el certificado se abre solo.
    var verCertificado by rememberSaveable { mutableStateOf(mensaje != null) }
    var verMovimientos by rememberSaveable { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp)
            .padding(bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        TarjetaPrincipal(certificado)

        val condicion = CondicionParametrica.campos(certificado.descripcionCobertura)
        TarjetaInformativa(titulo = "Coberturas", icono = Icons.Outlined.Shield) {
            val suma = Formatos.dinero(certificado.sumaAsegurada, certificado.moneda)
            Text(
                text = "${certificado.coberturaPrincipal} · Suma asegurada $suma",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
            certificado.descripcionCobertura?.takeIf { it.isNotBlank() && condicion.isEmpty() }?.let {
                Text(
                    text = it,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            }
            condicion.forEach { campo ->
                val valor = if (campo.esMoneda) {
                    Formatos.dinero(campo.valor, certificado.moneda)
                } else {
                    campo.valor
                }
                Dato(campo.etiqueta, valor)
            }
        }

        TarjetaInformativa(titulo = "Exclusiones principales", icono = Icons.Outlined.Info) {
            if (certificado.exclusionesPrincipales.isEmpty()) {
                Text(
                    text = "No se informan exclusiones principales para esta cobertura.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            } else {
                Text(
                    text = certificado.exclusionesPrincipales.joinToString(separator = "\n") { "• $it" },
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            }
        }

        if (mensaje != null) {
            SolventaNoticePill(text = mensaje, icon = painterResource(id = R.drawable.ic_main_page))
        }

        BotonAccion(
            texto = "Ver certificado y QR",
            icono = Icons.Outlined.Description,
            primario = true,
            onClick = { verCertificado = !verCertificado }
        )
        if (verCertificado) {
            SeccionCertificado(
                certificado = certificado,
                descargandoDocumento = descargandoDocumento,
                compartiendo = compartiendo,
                onVerDocumento = onVerDocumento,
                onCompartir = onCompartir
            )
        }

        BotonAccion(
            texto = "Consultar movimientos",
            icono = Icons.Outlined.History,
            onClick = { verMovimientos = !verMovimientos }
        )
        if (verMovimientos) {
            SeccionMovimientos(historial, cargandoHistorial, errorHistorial)
        }

        if (certificado.activa) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                BotonAccion(
                    texto = "Renovar",
                    icono = Icons.Outlined.Autorenew,
                    onClick = onRenovar,
                    modifier = Modifier.weight(1f)
                )
                BotonAccion(
                    texto = "Cancelar",
                    icono = Icons.Outlined.Cancel,
                    cancelar = true,
                    onClick = onCancelar,
                    modifier = Modifier.weight(1f)
                )
            }
        }
    }
}

@Composable
private fun TarjetaPrincipal(certificado: Certificado) {
    Surface(
        shape = RoundedCornerShape(20.dp),
        color = FondoEncabezado,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            EtiquetaEstado(estado = certificado.estado)
            Text(
                text = certificado.nombreRamo,
                style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
                color = Color.White
            )
            Text(
                text = "Póliza ${certificado.numeroPoliza} · " +
                    Formatos.vigencia(certificado.fechaInicio, certificado.fechaFin),
                style = MaterialTheme.typography.bodyMedium,
                color = Color.White.copy(alpha = 0.85f)
            )
            if (!certificado.activa) {
                Text(
                    text = "Esta póliza ya no está vigente. El certificado se conserva como constancia.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.White.copy(alpha = 0.7f)
                )
            }
        }
    }
}

@Composable
private fun TarjetaInformativa(
    titulo: String,
    icono: ImageVector,
    contenido: @Composable () -> Unit
) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, BordeTarjeta),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(modifier = Modifier.padding(16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Icon(
                imageVector = icono,
                contentDescription = null,
                tint = Navegacion,
                modifier = Modifier.size(24.dp)
            )
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(
                    text = titulo,
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                    color = MaterialTheme.colorScheme.onSurface
                )
                contenido()
            }
        }
    }
}

@Composable
private fun BotonAccion(
    texto: String,
    icono: ImageVector,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    primario: Boolean = false,
    cancelar: Boolean = false
) {
    val forma = RoundedCornerShape(14.dp)
    val tamano = modifier
        .fillMaxWidth()
        .height(52.dp)
    if (primario) {
        Button(
            onClick = onClick,
            shape = forma,
            colors = ButtonDefaults.buttonColors(containerColor = Navegacion, contentColor = Color.White),
            modifier = tamano
        ) { ContenidoBoton(texto, icono) }
    } else {
        OutlinedButton(
            onClick = onClick,
            shape = forma,
            border = BorderStroke(1.dp, if (cancelar) BordeCancelar else BordeTarjeta),
            colors = ButtonDefaults.outlinedButtonColors(
                containerColor = if (cancelar) FondoCancelar else Color.Transparent,
                contentColor = if (cancelar) RojoCancelar else MaterialTheme.colorScheme.onSurface
            ),
            modifier = tamano
        ) { ContenidoBoton(texto, icono) }
    }
}

@Composable
private fun ContenidoBoton(texto: String, icono: ImageVector) {
    Icon(imageVector = icono, contentDescription = null, modifier = Modifier.size(20.dp))
    Spacer(modifier = Modifier.size(10.dp))
    Text(text = texto, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
}

@Composable
private fun SeccionCertificado(
    certificado: Certificado,
    descargandoDocumento: Boolean,
    compartiendo: Boolean,
    onVerDocumento: () -> Unit,
    onCompartir: () -> Unit
) {
    Seccion("Información de la póliza") {
        Dato("Número de póliza", certificado.numeroPoliza)
        Dato("Titular", certificado.titular)
        Dato("Documento", certificado.documentoTitular)
        Dato("Vigencia", Formatos.vigencia(certificado.fechaInicio, certificado.fechaFin))
        certificado.emitidaEn.takeIf { it.isNotBlank() }?.let {
            Dato("Fecha de emisión", Formatos.fechaHora(it))
        }
        certificado.primaTotal.takeIf { it.isNotBlank() }?.let {
            Dato("Prima total", Formatos.dinero(it, certificado.moneda))
        }
    }

    SolventaPrimaryButton(
        text = "Ver documento PDF",
        onClick = onVerDocumento,
        isLoading = descargandoDocumento
    )

    SolventaSecondaryButton(
        text = "Compartir certificado",
        onClick = onCompartir,
        isLoading = compartiendo
    )
    Text(
        text = "Se genera un enlace temporal: quien lo reciba verá el certificado hasta que venza.",
        style = MaterialTheme.typography.labelMedium,
        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
    )

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text(
            text = "Certificado digital",
            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
            color = MaterialTheme.colorScheme.onSurface
        )
        SolventaCodigoQr(
            contenido = certificado.contenidoQr,
            descripcion = "Código QR de la póliza ${certificado.numeroPoliza}"
        )
    }
}

@Composable
private fun SeccionMovimientos(
    historial: HistorialEndosos?,
    cargandoHistorial: Boolean,
    errorHistorial: String?
) {
    Seccion("Movimientos de la póliza") {
        when {
            historial == null && cargandoHistorial -> CircularProgressIndicator(
                color = Navegacion,
                modifier = Modifier
                    .size(24.dp)
                    .semantics { contentDescription = "Cargando movimientos" }
            )
            historial == null && errorHistorial != null -> Text(
                text = errorHistorial,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error
            )
            historial?.endosos.isNullOrEmpty() -> Text(
                text = "Esta póliza no tiene movimientos registrados.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
            else -> historial?.endosos.orEmpty().forEachIndexed { indice, endoso ->
                if (indice > 0) HorizontalDivider()
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        text = endoso.tipo.etiquetaMovimiento(),
                        style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Text(
                        text = Formatos.fecha(endoso.fechaEfecto),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                    )
                    endoso.cambios.forEach { cambio ->
                        Text(
                            text = cambio.descripcion,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun Seccion(
    titulo: String,
    contenido: @Composable () -> Unit
) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = titulo,
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
            contenido()
        }
    }
}

private fun String.etiquetaMovimiento(): String =
    lowercase().replace('_', ' ').replaceFirstChar { it.titlecase() }

@Composable
private fun Dato(etiqueta: String, valor: String) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(
            text = etiqueta,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
        )
        Text(
            text = valor,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurface
        )
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun CertificateScreenPreview() {
    SolventaTheme {
        CertificateScreen(
            certificado = Certificado(
                polizaId = "1",
                numeroPoliza = "SOL-VJ-0001",
                nombreRamo = "Seguro de viaje",
                estado = EstadoPoliza.VIGENTE,
                activa = true,
                titular = "Ana Pérez",
                documentoTitular = "CC ****5678",
                fechaInicio = "2026-10-01",
                fechaFin = "2026-12-31",
                coberturaPrincipal = "Asistencia médica en viaje",
                sumaAsegurada = "40000000.00",
                moneda = "COP",
                contenidoQr = "SOLVENTA|SOL-VJ-0001|a1b2c3d4"
            ),
            cargando = false,
            error = null,
            historial = HistorialEndosos(emptyList()),
            cargandoHistorial = false,
            errorHistorial = null,
            descargandoDocumento = false,
            compartiendo = false,
            mensaje = null,
            onVerDocumento = {},
            onCompartir = {},
            onReintentar = {},
            onVolver = {}
        )
    }
}
