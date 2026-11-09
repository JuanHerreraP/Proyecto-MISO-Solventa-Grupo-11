package com.example.solventa.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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
import com.example.solventa.ui.components.SolventaCodigoQr
import com.example.solventa.ui.components.SolventaNoticePill
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaSecondaryButton
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.SolventaTheme

/** Detalle contractual de la póliza, certificado e historial de movimientos (HU09). */
@Composable
fun CertificateScreen(
    certificado: Certificado?,
    cargando: Boolean,
    error: String?,
    descargandoDocumento: Boolean,
    compartiendo: Boolean,
    mensaje: String?,
    onVerDocumento: () -> Unit,
    onCompartir: () -> Unit,
    onVerHistorial: () -> Unit,
    onReintentar: () -> Unit,
    onVolver: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
        Column(modifier = Modifier.fillMaxSize()) {
            Encabezado(titulo = "Detalle de póliza", onVolver = onVolver)

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
                    descargandoDocumento = descargandoDocumento,
                    compartiendo = compartiendo,
                    mensaje = mensaje,
                    onVerDocumento = onVerDocumento,
                    onCompartir = onCompartir,
                    onVerHistorial = onVerHistorial
                )
            }
        }
    }
}

@Composable
private fun Contenido(
    certificado: Certificado,
    descargandoDocumento: Boolean,
    compartiendo: Boolean,
    mensaje: String?,
    onVerDocumento: () -> Unit,
    onCompartir: () -> Unit,
    onVerHistorial: () -> Unit
) {
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
                text = certificado.nombreRamo,
                style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.onBackground
            )
            EtiquetaEstado(estado = certificado.estado)
            if (!certificado.activa) {
                Text(
                    text = "Esta póliza ya no está vigente. El certificado se conserva como constancia.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            }
        }

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

        Seccion("Cobertura contratada", destacada = true) {
            Dato("Cobertura principal", certificado.coberturaPrincipal)
            certificado.descripcionCobertura?.takeIf { it.isNotBlank() }?.let {
                Text(
                    text = it,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.75f)
                )
            }
            Dato("Suma asegurada", Formatos.dinero(certificado.sumaAsegurada, certificado.moneda))
        }

        val condicion = CondicionParametrica.campos(certificado.descripcionCobertura)
        if (condicion.isNotEmpty()) {
            Surface(
                shape = RoundedCornerShape(16.dp),
                color = Navegacion.copy(alpha = 0.06f),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text(
                        text = "Condición paramétrica",
                        style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                        color = Navegacion
                    )
                    condicion.forEach { campo ->
                        val valor = if (campo.esMoneda) {
                            Formatos.dinero(campo.valor, certificado.moneda)
                        } else {
                            campo.valor
                        }
                        Dato(campo.etiqueta, valor)
                    }
                }
            }
        }

        Seccion("Exclusiones principales") {
            if (certificado.exclusionesPrincipales.isEmpty()) {
                Text(
                    text = "No se informan exclusiones principales para esta cobertura.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            } else {
                certificado.exclusionesPrincipales.forEach { exclusion ->
                    Text(
                        text = "• $exclusion",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }
        }

        Seccion("Historial de movimientos") {
            Text(
                text = "Consulta los endosos y cambios registrados sobre esta póliza.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.75f)
            )
            SolventaSecondaryButton(
                text = "Ver historial de la póliza",
                onClick = onVerHistorial
            )
        }

        if (mensaje != null) {
            SolventaNoticePill(text = mensaje, icon = painterResource(id = R.drawable.ic_main_page))
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
}

@Composable
private fun Seccion(
    titulo: String,
    destacada: Boolean = false,
    contenido: @Composable () -> Unit
) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = if (destacada) Navegacion.copy(alpha = 0.06f)
        else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = titulo,
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                color = if (destacada) Navegacion else MaterialTheme.colorScheme.onSurface
            )
            contenido()
        }
    }
}

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
            descargandoDocumento = false,
            compartiendo = false,
            mensaje = null,
            onVerDocumento = {},
            onCompartir = {},
            onVerHistorial = {},
            onReintentar = {},
            onVolver = {}
        )
    }
}
