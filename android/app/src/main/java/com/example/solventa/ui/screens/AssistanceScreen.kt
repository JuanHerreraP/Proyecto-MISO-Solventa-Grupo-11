package com.example.solventa.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
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
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.asistencias.Asistencia
import com.example.solventa.domain.asistencias.EstadoAsistencia
import com.example.solventa.domain.asistencias.EstadoAsistencias
import com.example.solventa.domain.asistencias.PasoAsistencia
import com.example.solventa.domain.asistencias.PrestadorCercano
import com.example.solventa.domain.asistencias.ServicioAsistencia
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaSecondaryButton
import com.example.solventa.ui.theme.Atencion
import com.example.solventa.ui.theme.Avance
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.R
import com.example.solventa.i18n.tr

/** Una póliza elegible para asistencia (vigente y de un ramo con servicios). */
data class PolizaAsistenciaElegible(
    val polizaId: String,
    val etiqueta: String
)

/**
 * Pantalla de asistencia en sitio (HU06). Un solo flujo por pasos gobernado por [estado]; el
 * mapa se dibuja en [MapaPrestadores], separado para poder probar la pantalla sin un mapa real.
 */
@Composable
fun AssistanceScreen(
    estado: EstadoAsistencias,
    polizasElegibles: List<PolizaAsistenciaElegible>,
    tienePermisoUbicacion: Boolean,
    onSeleccionarPoliza: (PolizaAsistenciaElegible) -> Unit,
    onSeleccionarServicio: (ServicioAsistencia) -> Unit,
    onSolicitarPermiso: () -> Unit,
    onBuscarPrestadores: (Double) -> Unit,
    onSeleccionarPrestador: (PrestadorCercano) -> Unit,
    onConfirmarSolicitud: (String?) -> Unit,
    onVerMisAsistencias: () -> Unit,
    onCancelarAsistencia: (String) -> Unit,
    onNuevaSolicitud: () -> Unit,
    onVolver: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
        Column(modifier = Modifier.fillMaxSize()) {
            Encabezado(
                titulo = tituloPaso(estado.paso),
                onVolver = onVolver,
                accion = {
                    if (estado.paso != PasoAsistencia.MIS_ASISTENCIAS) {
                        Text(
                            text = tr(R.string.assistance_mis_asistencias),
                            style = MaterialTheme.typography.labelMedium,
                            color = Navegacion,
                            modifier = Modifier
                                .padding(end = 12.dp)
                                .selectable(selected = false, onClick = onVerMisAsistencias)
                        )
                    }
                }
            )

            if (estado.error != null) {
                AvisoAsistencia(texto = estado.error, color = Atencion)
            } else if (estado.aviso != null) {
                AvisoAsistencia(texto = estado.aviso, color = Navegacion)
            }

            when (estado.paso) {
                PasoAsistencia.SELECCION_POLIZA -> PasoSeleccionPoliza(
                    polizas = polizasElegibles,
                    onSeleccionar = onSeleccionarPoliza
                )

                PasoAsistencia.SELECCION_SERVICIO -> PasoSeleccionServicio(
                    estado = estado,
                    onSeleccionar = onSeleccionarServicio
                )

                PasoAsistencia.PERMISO_UBICACION -> PasoPermisoUbicacion(
                    estado = estado,
                    tienePermiso = tienePermisoUbicacion,
                    onSolicitarPermiso = onSolicitarPermiso,
                    onBuscar = { onBuscarPrestadores(estado.radioKm) }
                )

                PasoAsistencia.PRESTADORES -> PasoPrestadores(
                    estado = estado,
                    onSeleccionar = onSeleccionarPrestador,
                    onReintentar = { onBuscarPrestadores(estado.radioKm) },
                    onAmpliarRadio = { onBuscarPrestadores(50.0) }
                )

                PasoAsistencia.CONFIRMACION -> PasoConfirmacion(
                    estado = estado,
                    onConfirmar = onConfirmarSolicitud,
                    onCancelar = onNuevaSolicitud
                )

                PasoAsistencia.EXITO -> PasoExito(
                    estado = estado,
                    onVerMisAsistencias = onVerMisAsistencias,
                    onVolverAlInicio = onVolver
                )

                PasoAsistencia.MIS_ASISTENCIAS -> PasoMisAsistencias(
                    estado = estado,
                    onCancelar = onCancelarAsistencia,
                    onNueva = onNuevaSolicitud
                )
            }
        }
    }
}

private fun tituloPaso(paso: PasoAsistencia): String = when (paso) {
    PasoAsistencia.SELECCION_POLIZA -> tr(R.string.assistance_asistencia_en_sitio)
    PasoAsistencia.SELECCION_SERVICIO -> tr(R.string.assistance_que_asistencia_necesitas)
    PasoAsistencia.PERMISO_UBICACION -> tr(R.string.assistance_tu_ubicacion)
    PasoAsistencia.PRESTADORES -> tr(R.string.assistance_prestadores_cercanos)
    PasoAsistencia.CONFIRMACION -> tr(R.string.assistance_confirmar_asistencia)
    PasoAsistencia.EXITO -> tr(R.string.assistance_asistencia_solicitada)
    PasoAsistencia.MIS_ASISTENCIAS -> tr(R.string.assistance_mis_asistencias)
}

@Composable
private fun PasoSeleccionPoliza(
    polizas: List<PolizaAsistenciaElegible>,
    onSeleccionar: (PolizaAsistenciaElegible) -> Unit
) {
    ColumnaConScroll {
        Text(
            text = tr(R.string.assistance_selecciona_una_poliza),
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurface
        )
        Text(
            text = tr(R.string.assistance_solo_aparecen_tus_polizas_vigentes),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
        )
        if (polizas.isEmpty()) {
            Text(
                text = tr(R.string.assistance_no_tienes_polizas_vigentes_con),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
        }
        polizas.forEach { poliza ->
            Tarjeta {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = poliza.etiqueta,
                        style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.size(8.dp))
                    SolventaPrimaryButton(
                        text = tr(R.string.assistance_seleccionar),
                        onClick = { onSeleccionar(poliza) }
                    )
                }
            }
        }
    }
}

@Composable
private fun PasoSeleccionServicio(
    estado: EstadoAsistencias,
    onSeleccionar: (ServicioAsistencia) -> Unit
) {
    ColumnaConScroll {
        estado.polizaSeleccionadaEtiqueta?.let {
            Text(
                text = it,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
        }
        when {
            estado.cargando -> Cargando(tr(R.string.assistance_cargando_servicios))
            estado.servicios.isEmpty() -> Text(
                text = tr(R.string.assistance_esta_poliza_no_ofrece_servicios),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
            else -> estado.servicios.forEach { servicio ->
                Tarjeta {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .selectable(
                                selected = estado.servicioSeleccionado?.codigo == servicio.codigo,
                                onClick = { onSeleccionar(servicio) }
                            )
                            .padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        RadioButton(
                            selected = estado.servicioSeleccionado?.codigo == servicio.codigo,
                            onClick = { onSeleccionar(servicio) }
                        )
                        Spacer(modifier = Modifier.size(8.dp))
                        Text(
                            text = servicio.nombre,
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
private fun PasoPermisoUbicacion(
    estado: EstadoAsistencias,
    tienePermiso: Boolean,
    onSolicitarPermiso: () -> Unit,
    onBuscar: () -> Unit
) {
    ColumnaConScroll {
        if (estado.permisoDenegado) {
            Text(
                text = tr(R.string.assistance_necesitamos_tu_ubicacion_para_encontrar) +
                    tr(R.string.assistance_puedes_habilitarla_desde_los_permisos),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.85f)
            )
            SolventaPrimaryButton(text = tr(R.string.assistance_reintentar), onClick = onSolicitarPermiso)
        } else {
            Text(
                text = tr(R.string.assistance_asistencia_necesita_tu_ubicacion_para),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.85f)
            )
            if (tienePermiso) {
                SolventaPrimaryButton(text = tr(R.string.assistance_buscar_prestadores_cercanos), onClick = onBuscar)
            } else {
                SolventaPrimaryButton(text = tr(R.string.assistance_permitir_ubicacion), onClick = onSolicitarPermiso)
            }
        }
    }
}

@Composable
private fun PasoPrestadores(
    estado: EstadoAsistencias,
    onSeleccionar: (PrestadorCercano) -> Unit,
    onReintentar: () -> Unit,
    onAmpliarRadio: () -> Unit
) {
    ColumnaConScroll {
        when {
            estado.cargando -> Cargando(tr(R.string.assistance_buscando_prestadores))
            estado.prestadores.isEmpty() -> {
                Text(
                    text = tr(R.string.assistance_no_encontramos_prestadores_disponibles_dentro) +
                        "${estado.radioKm.toInt()} km.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.85f)
                )
                SolventaPrimaryButton(text = tr(R.string.assistance_reintentar), onClick = onReintentar)
                if (estado.radioKm < 50.0) {
                    SolventaSecondaryButton(text = tr(R.string.assistance_ampliar_a_50_km), onClick = onAmpliarRadio)
                }
            }
            else -> {
                MapaPrestadores(estado = estado, modifier = Modifier.fillMaxWidth().height(220.dp))
                Text(
                    text = tr(R.string.assistance_prestadores_cercanos),
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface
                )
                estado.prestadores.forEach { prestador ->
                    TarjetaPrestador(prestador = prestador, onSeleccionar = onSeleccionar)
                }
            }
        }
    }
}

@Composable
private fun TarjetaPrestador(
    prestador: PrestadorCercano,
    onSeleccionar: (PrestadorCercano) -> Unit
) {
    Tarjeta {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                text = prestador.nombre,
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = "${formatoKm(prestador.distanciaKm)} · ${prestador.tipoServicio.etiqueta}",
                style = MaterialTheme.typography.labelMedium,
                color = Navegacion
            )
            if (prestador.direccion.isNotBlank()) {
                Text(
                    text = prestador.direccion,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            }
            Spacer(modifier = Modifier.size(4.dp))
            SolventaPrimaryButton(
                text = tr(R.string.assistance_seleccionar),
                onClick = { onSeleccionar(prestador) }
            )
        }
    }
}

@Composable
private fun PasoConfirmacion(
    estado: EstadoAsistencias,
    onConfirmar: (String?) -> Unit,
    onCancelar: () -> Unit
) {
    var observaciones by rememberSaveable { mutableStateOf("") }
    val prestador = estado.prestadorSeleccionado
    ColumnaConScroll {
        FilaDato(tr(R.string.assistance_poliza), estado.polizaSeleccionadaEtiqueta ?: "—")
        FilaDato(tr(R.string.assistance_servicio), estado.servicioSeleccionado?.nombre ?: "—")
        FilaDato(tr(R.string.assistance_prestador), prestador?.nombre ?: "—")
        if (prestador != null) {
            FilaDato(tr(R.string.assistance_distancia), formatoKm(prestador.distanciaKm))
        }
        FilaDato(tr(R.string.assistance_ubicacion_de_atencion), tr(R.string.assistance_ubicacion_actual))
        OutlinedTextField(
            value = observaciones,
            onValueChange = { if (it.length <= 500) observaciones = it },
            label = { Text(tr(R.string.assistance_observaciones_opcional)) },
            modifier = Modifier.fillMaxWidth().heightIn(min = 96.dp),
            supportingText = { Text("${observaciones.length}/500") }
        )
        SolventaPrimaryButton(
            text = if (estado.solicitando) tr(R.string.assistance_solicitando_asistencia) else tr(R.string.assistance_solicitar_asistencia),
            onClick = { onConfirmar(observaciones.ifBlank { null }) },
            enabled = !estado.solicitando,
            isLoading = estado.solicitando
        )
        SolventaSecondaryButton(
            text = tr(R.string.assistance_cancelar),
            onClick = onCancelar,
            enabled = !estado.solicitando
        )
    }
}

@Composable
private fun PasoExito(
    estado: EstadoAsistencias,
    onVerMisAsistencias: () -> Unit,
    onVolverAlInicio: () -> Unit
) {
    val asistencia = estado.asistenciaCreada
    ColumnaConScroll {
        Text(
            text = tr(R.string.assistance_tu_solicitud_fue_registrada_correctamente),
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurface
        )
        if (asistencia != null) {
            FilaDato(tr(R.string.assistance_solicitud), asistencia.asistenciaId)
            FilaDato(tr(R.string.assistance_prestador), asistencia.prestador.nombre)
            FilaDato(tr(R.string.assistance_servicio), asistencia.servicio.etiqueta)
            FilaDato(tr(R.string.assistance_estado), asistencia.estado.etiqueta)
        }
        SolventaPrimaryButton(text = tr(R.string.assistance_ver_mis_asistencias), onClick = onVerMisAsistencias)
        SolventaSecondaryButton(text = tr(R.string.assistance_volver_al_inicio), onClick = onVolverAlInicio)
    }
}

@Composable
private fun PasoMisAsistencias(
    estado: EstadoAsistencias,
    onCancelar: (String) -> Unit,
    onNueva: () -> Unit
) {
    ColumnaConScroll {
        when {
            estado.cargandoAsistencias -> Cargando(tr(R.string.assistance_cargando_tus_asistencias))
            estado.asistencias.isEmpty() -> Text(
                text = tr(R.string.assistance_aun_no_tienes_asistencias_solicitadas),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
            else -> estado.asistencias.forEach { asistencia ->
                TarjetaAsistencia(
                    asistencia = asistencia,
                    cancelando = estado.cancelandoId == asistencia.asistenciaId,
                    onCancelar = { onCancelar(asistencia.asistenciaId) }
                )
            }
        }
        SolventaSecondaryButton(text = tr(R.string.assistance_nueva_solicitud), onClick = onNueva)
    }
}

@Composable
private fun TarjetaAsistencia(
    asistencia: Asistencia,
    cancelando: Boolean,
    onCancelar: () -> Unit
) {
    Tarjeta {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                text = asistencia.servicio.etiqueta,
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = asistencia.prestador.nombre,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f)
            )
            EtiquetaEstadoAsistencia(asistencia.estado)
            SeguimientoAsistencia(asistencia)
            if (asistencia.cancelable) {
                Spacer(modifier = Modifier.size(4.dp))
                SolventaSecondaryButton(
                    text = if (cancelando) tr(R.string.assistance_cancelando) else tr(R.string.assistance_cancelar_asistencia),
                    onClick = onCancelar,
                    enabled = !cancelando,
                    isLoading = cancelando
                )
            }
        }
    }
}

/**
 * Texto de seguimiento según el estado (HU06 ampliación):
 *  - SOLICITADA: esperando aceptación, sin ETA.
 *  - ACEPTADA: el prestador aceptó + "Tiempo estimado de llegada" (minutos o "Aún no disponible").
 *  - CANCELADA: sin ETA activo.
 */
@Composable
private fun SeguimientoAsistencia(asistencia: Asistencia) {
    when (asistencia.estado) {
        EstadoAsistencia.SOLICITADA -> Text(
            text = tr(R.string.assistance_esperando_aceptacion_del_prestador),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
        )

        EstadoAsistencia.ACEPTADA -> {
            Text(
                text = tr(R.string.assistance_el_prestador_acepto_tu_solicitud),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
            FilaDato(
                etiqueta = tr(R.string.assistance_tiempo_estimado_de_llegada),
                valor = asistencia.tiempoEstimadoLlegadaMinutos
                    ?.let { "$it min" }
                    ?: tr(R.string.assistance_aun_no_disponible)
            )
        }

        EstadoAsistencia.CANCELADA -> {
            // No se muestra ETA como información activa en una asistencia cancelada.
        }
    }
}

@Composable
private fun EtiquetaEstadoAsistencia(estado: EstadoAsistencia) {
    val color = when (estado) {
        EstadoAsistencia.CANCELADA -> Atencion
        EstadoAsistencia.ACEPTADA -> Avance
        EstadoAsistencia.SOLICITADA -> Navegacion
    }
    Surface(shape = RoundedCornerShape(8.dp), color = color.copy(alpha = 0.15f)) {
        Text(
            text = estado.etiqueta,
            style = MaterialTheme.typography.labelMedium,
            color = color,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
        )
    }
}

@Composable
private fun FilaDato(etiqueta: String, valor: String) {
    Column {
        Text(
            text = etiqueta,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
        )
        Text(
            text = valor,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface
        )
    }
}

@Composable
private fun AvisoAsistencia(texto: String, color: androidx.compose.ui.graphics.Color) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = color.copy(alpha = 0.12f),
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp, vertical = 4.dp)
    ) {
        Text(
            text = texto,
            style = MaterialTheme.typography.bodyMedium,
            color = color,
            modifier = Modifier.padding(12.dp)
        )
    }
}

@Composable
private fun Cargando(descripcion: String) {
    Box(
        modifier = Modifier.fillMaxWidth().padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        CircularProgressIndicator(
            color = Navegacion,
            modifier = Modifier.semantics { contentDescription = descripcion }
        )
    }
}

@Composable
private fun ColumnaConScroll(contenido: @Composable () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        contenido()
    }
}

@Composable
private fun Tarjeta(contenido: @Composable () -> Unit) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
        modifier = Modifier.fillMaxWidth()
    ) {
        contenido()
    }
}

/** "0,5 km" o "1,8 km" con coma decimal, como en el resto de la app. */
internal fun formatoKm(distanciaKm: Double): String {
    val redondeado = (distanciaKm * 10).toLong() / 10.0
    return "%.1f km".format(redondeado).replace('.', ',')
}
