package com.example.solventa.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.automirrored.outlined.ManageSearch
import androidx.compose.material.icons.outlined.NotificationsNone
import androidx.compose.material.icons.outlined.PersonOutline
import androidx.compose.material.icons.outlined.PersonAddAlt
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.SupportAgent
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.rememberVectorPainter
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.R
import com.example.solventa.domain.auth.Perfil
import com.example.solventa.domain.polizas.Formatos
import com.example.solventa.domain.polizas.MovimientoReciente
import com.example.solventa.domain.polizas.NaturalezaMonto
import com.example.solventa.domain.polizas.TipoMovimiento
import com.example.solventa.ui.components.SolventaNoticePill
import com.example.solventa.ui.components.SolventaBottomNavigation
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.Noche
import com.example.solventa.ui.theme.SolventaTheme
import com.example.solventa.i18n.tr

/** Inicio privado del cliente. Conserva las funciones de sesión y billetera. */
@Composable
fun HomeScreen(
    perfil: Perfil,
    biometriaActivada: Boolean,
    biometriaDisponible: Boolean,
    ofrecerActivarBiometria: Boolean,
    mensaje: String?,
    cerrandoSesion: Boolean,
    onActivarBiometria: () -> Unit,
    onSolicitarActivacion: () -> Unit,
    onDescartarActivacion: () -> Unit,
    onCerrarSesion: () -> Unit,
    modifier: Modifier = Modifier,
    onVerBilletera: (() -> Unit)? = null,
    onVerCotizaciones: (() -> Unit)? = null,
    onVerPagos: (() -> Unit)? = null,
    onVerSiniestros: (() -> Unit)? = null,
    onVerAsistencia: (() -> Unit)? = null,
    onNavbarPolizas: (() -> Unit)? = null,
    onNavbarSiniestros: (() -> Unit)? = null,
    onVerPerfil: (() -> Unit)? = null,
    onCotizarSeguro: () -> Unit = {},
    cantidadPolizasActivas: Int? = null,
    movimientosRecientes: List<MovimientoReciente> = emptyList(),
    cargandoMovimientosRecientes: Boolean = false,
    onVerHistorialPoliza: (String) -> Unit = {},
    onCrearAsesor: (() -> Unit)? = null,
    onCrearAnalista: (() -> Unit)? = null,
    sinConexion: Boolean = false,
    ultimaSincronizacionMs: Long? = null,
    notificacionesSinLeer: Int = 0,
    onVerNotificaciones: (() -> Unit)? = null
) {
    if (ofrecerActivarBiometria) {
        AlertDialog(
            onDismissRequest = onDescartarActivacion,
            title = { Text(tr(R.string.home_activar_ingreso_con_huella)) },
            text = {
                Text(
                    tr(R.string.home_la_proxima_vez_podras_entrar) +
                        tr(R.string.home_tu_biometria_no_sale_del)
                )
            },
            confirmButton = { TextButton(onClick = onActivarBiometria) { Text(tr(R.string.home_activar)) } },
            dismissButton = { TextButton(onClick = onDescartarActivacion) { Text(tr(R.string.home_ahora_no)) } }
        )
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        bottomBar = {
            SolventaBottomNavigation(
                onCotizaciones = onVerCotizaciones,
                onPolizas = onNavbarPolizas ?: onVerBilletera,
                onSiniestros = onNavbarSiniestros ?: onVerSiniestros,
                onPagos = onVerPagos
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            EncabezadoInicio(notificacionesSinLeer, onVerNotificaciones, onVerPerfil)

            Text(
                text = tr(R.string.advisor_home_hola, perfil.nombre),
                style = MaterialTheme.typography.headlineLarge,
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = tr(R.string.home_todo_lo_importante_de_tu),
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
            )

            TarjetaBilletera(
                cantidadPolizasActivas = cantidadPolizasActivas,
                onVerBilletera = onVerBilletera,
                onCotizarSeguro = onCotizarSeguro,
                sinConexion = sinConexion,
                ultimaSincronizacionMs = ultimaSincronizacionMs
            )

            if (onVerAsistencia != null) {
                BotonAsistencia(onClick = onVerAsistencia)
            }

            HistorialReciente(
                movimientos = movimientosRecientes,
                cargando = cargandoMovimientosRecientes,
                onVerHistorialPoliza = onVerHistorialPoliza
            )

            if (onCrearAsesor != null) {
                Surface(
                    shape = RoundedCornerShape(18.dp),
                    color = Navegacion.copy(alpha = 0.1f),
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable(role = Role.Button, onClick = onCrearAsesor)
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Outlined.PersonAddAlt, contentDescription = null, tint = Navegacion)
                        Spacer(modifier = Modifier.width(12.dp))
                        Text(
                            text = tr(R.string.advisor_home_crear_un_asesor_de_ventas),
                            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                }
            }

            if (onCrearAnalista != null) {
                Surface(
                    shape = RoundedCornerShape(18.dp),
                    color = Navegacion.copy(alpha = 0.1f),
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable(role = Role.Button, onClick = onCrearAnalista)
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.AutoMirrored.Outlined.ManageSearch, contentDescription = null, tint = Navegacion)
                        Spacer(modifier = Modifier.width(12.dp))
                        Text(
                            text = tr(R.string.home_crear_un_analista_de_cumplimiento),
                            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                }
            }

            if (mensaje != null) {
                SolventaNoticePill(
                    text = mensaje,
                    icon = rememberVectorPainter(Icons.Outlined.Shield)
                )
            }

            if (!biometriaActivada && biometriaDisponible) {
                TextButton(onClick = onSolicitarActivacion) {
                    Text(tr(R.string.home_activar_ingreso_con_huella_2), color = Navegacion)
                }
            }

        }
    }
}

@Composable
private fun EncabezadoInicio(
    sinLeer: Int,
    onVerNotificaciones: (() -> Unit)?,
    onVerPerfil: (() -> Unit)?
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Image(
                painter = painterResource(id = R.drawable.solventa_shield),
                contentDescription = tr(R.string.biometrical_login_escudo_de_solventa),
                modifier = Modifier.size(28.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "Solventa",
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.onSurface
            )
        }
        Row {
            IconButton(onClick = { onVerNotificaciones?.invoke() }, enabled = onVerNotificaciones != null) {
                BadgedBox(
                    badge = {
                        if (sinLeer > 0) {
                            Badge { Text(if (sinLeer > 99) "99+" else sinLeer.toString()) }
                        }
                    }
                ) {
                    Icon(
                        imageVector = Icons.Outlined.NotificationsNone,
                        contentDescription = if (sinLeer > 0) {
                            tr(R.string.home_notificaciones_sin_leer, sinLeer)
                        } else {
                            tr(R.string.home_notificaciones)
                        },
                        tint = MaterialTheme.colorScheme.onSurface
                    )
                }
            }
            IconButton(onClick = { onVerPerfil?.invoke() }, enabled = onVerPerfil != null) {
                Icon(
                    imageVector = Icons.Outlined.PersonOutline,
                    contentDescription = tr(R.string.home_perfil),
                    tint = MaterialTheme.colorScheme.onSurface
                )
            }
        }
    }
}

@Composable
private fun TarjetaBilletera(
    cantidadPolizasActivas: Int?,
    onVerBilletera: (() -> Unit)?,
    onCotizarSeguro: () -> Unit,
    sinConexion: Boolean,
    ultimaSincronizacionMs: Long?
) {
    Surface(
        shape = RoundedCornerShape(24.dp),
        color = Noche,
        modifier = Modifier
            .fillMaxWidth()
            .then(
                if (onVerBilletera == null) Modifier else Modifier.clickable(
                    role = Role.Button,
                    onClickLabel = tr(R.string.home_ver_mi_billetera),
                    onClick = onVerBilletera
                )
            )
    ) {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                text = tr(R.string.home_billetera_de_polizas),
                style = MaterialTheme.typography.bodyMedium,
                color = Color.White.copy(alpha = 0.7f)
            )
            Text(
                text = textoPolizas(cantidadPolizasActivas),
                style = MaterialTheme.typography.headlineMedium,
                color = Color.White
            )
            InlineSyncStatus(
                sinConexion = sinConexion,
                ultimaSincronizacionMs = ultimaSincronizacionMs
            )
            if (onVerBilletera != null) {
                Text(
                    text = tr(R.string.home_ver_mi_billetera),
                    style = MaterialTheme.typography.labelMedium,
                    color = Color.White.copy(alpha = 0.75f)
                )
            }
            Row(
                modifier = Modifier
                    .clickable(role = Role.Button, onClick = onCotizarSeguro)
                    .heightIn(min = 48.dp)
                    .padding(vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = tr(R.string.home_cotizar_un_nuevo_seguro),
                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                    color = Color.White
                )
                Spacer(modifier = Modifier.width(6.dp))
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp),
                    tint = Color.White
                )
            }
        }
    }
}

private fun textoPolizas(cantidad: Int?): String = when (cantidad) {
    null -> tr(R.string.home_consulta_tus_polizas)
    1 -> tr(R.string.home_1_poliza_activa)
    else -> tr(R.string.home_polizas_activas, cantidad)
}

@Composable
private fun HistorialReciente(
    movimientos: List<MovimientoReciente>,
    cargando: Boolean,
    onVerHistorialPoliza: (String) -> Unit
) {
    Surface(
        shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.surfaceContainer,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = tr(R.string.home_historial_reciente),
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
            when {
                cargando -> Text(
                    text = tr(R.string.home_cargando_movimientos),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
                )
                movimientos.isEmpty() -> Text(
                    text = tr(R.string.home_aun_no_tienes_movimientos_registrados),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
                )
                else -> movimientos.forEachIndexed { indice, reciente ->
                    if (indice > 0) HorizontalDivider(color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f))
                    FilaMovimientoReciente(reciente, onVerHistorialPoliza)
                }
            }
        }
    }
}

@Composable
private fun FilaMovimientoReciente(
    reciente: MovimientoReciente,
    onVerHistorialPoliza: (String) -> Unit
) {
    val movimiento = reciente.movimiento
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(role = Role.Button, onClick = { onVerHistorialPoliza(movimiento.polizaId) })
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.Top
    ) {
        Text(
            text = Formatos.fecha(movimiento.fecha),
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f),
            modifier = Modifier.width(72.dp)
        )
        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(
                text = movimiento.tipo.tituloCorto(),
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = reciente.nombreRamo,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
            )
        }
        Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                text = movimiento.monto?.let {
                    montoMovimiento(it, movimiento.moneda, movimiento.naturalezaMonto)
                } ?: "—",
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                color = MaterialTheme.colorScheme.onSurface
            )
            movimiento.estado?.let { EstadoMovimiento(it) }
        }
    }
}

@Composable
private fun EstadoMovimiento(estado: String) {
    Surface(shape = RoundedCornerShape(50), color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f)) {
        Text(
            text = estado,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f),
            modifier = Modifier.padding(horizontal = 7.dp, vertical = 3.dp)
        )
    }
}

@Composable
private fun BotonAsistencia(onClick: () -> Unit) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .height(72.dp)
            .clickable(role = Role.Button, onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        color = Navegacion.copy(alpha = 0.1f)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(shape = RoundedCornerShape(12.dp), color = Navegacion.copy(alpha = 0.12f)) {
                Icon(
                    imageVector = Icons.Outlined.SupportAgent,
                    contentDescription = null,
                    tint = Navegacion,
                    modifier = Modifier.padding(10.dp).size(22.dp)
                )
            }
            Text(
                text = tr(R.string.assistance_asistencia_en_sitio),
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}

private fun TipoMovimiento.tituloCorto(): String = when (this) {
    TipoMovimiento.EMISION -> tr(R.string.home_emision_de_poliza)
    TipoMovimiento.PAGO_PRIMA_INICIAL -> tr(R.string.home_pago_de_prima_inicial)
    TipoMovimiento.ENDOSO -> tr(R.string.home_modificacion_contractual)
    TipoMovimiento.RENOVACION -> tr(R.string.home_renovacion)
    TipoMovimiento.CANCELACION -> tr(R.string.home_cancelacion)
    TipoMovimiento.DESEMBOLSO_INDEMNIZACION -> tr(R.string.home_pago_de_indemnizacion)
    TipoMovimiento.REEMBOLSO -> tr(R.string.home_reembolso)
}

private fun montoMovimiento(monto: String, moneda: String?, naturaleza: NaturalezaMonto?): String {
    val formateado = Formatos.dinero(monto, moneda ?: "COP")
    return when (naturaleza) {
        NaturalezaMonto.COBRO -> "−$formateado"
        NaturalezaMonto.REEMBOLSO, NaturalezaMonto.INDEMNIZACION -> "+$formateado"
        else -> formateado
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun HomeScreenPreview() {
    SolventaTheme {
        HomeScreen(
            perfil = Perfil("u-1", "Ana", "Pérez", "ana@gmail.com", "CLIENTE"),
            biometriaActivada = true,
            biometriaDisponible = true,
            ofrecerActivarBiometria = false,
            mensaje = null,
            cerrandoSesion = false,
            onActivarBiometria = {},
            onSolicitarActivacion = {},
            onDescartarActivacion = {},
            onCerrarSesion = {},
            onVerBilletera = {},
            onVerCotizaciones = {},
            onCotizarSeguro = {},
            cantidadPolizasActivas = 2
        )
    }
}
