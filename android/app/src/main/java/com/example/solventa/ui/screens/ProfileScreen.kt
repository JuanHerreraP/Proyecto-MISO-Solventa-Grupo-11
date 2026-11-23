package com.example.solventa.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.automirrored.outlined.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.outlined.Logout
import androidx.compose.material.icons.outlined.Language
import androidx.compose.material.icons.outlined.NotificationsNone
import androidx.compose.material.icons.outlined.PersonOutline
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.disabled
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.auth.Perfil
import com.example.solventa.ui.components.SolventaBottomNavigation
import com.example.solventa.ui.theme.Avance
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.Noche
import com.example.solventa.R
import com.example.solventa.i18n.tr
import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.material3.RadioButton
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import com.example.solventa.i18n.Idioma

@Composable
fun ProfileScreen(
    perfil: Perfil,
    biometriaActivada: Boolean,
    sinConexion: Boolean,
    cerrandoSesion: Boolean,
    onCerrarSesion: () -> Unit,
    onInicio: () -> Unit,
    onPolizas: (() -> Unit)?,
    onSiniestros: (() -> Unit)?,
    onCotizaciones: (() -> Unit)? = null,
    onPagos: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
    notificaciones: PreferenciasNotificacionesUi? = null,
    onCambiarPush: (Boolean) -> Unit = {},
    onSolicitarPermisoNotificaciones: () -> Unit = {},
    onAbrirAjustesNotificaciones: () -> Unit = {}
) {
    var seccion by rememberSaveable { mutableStateOf<SeccionPerfil?>(null) }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        bottomBar = {
            SolventaBottomNavigation(
                onInicio = onInicio,
                onCotizaciones = onCotizaciones,
                onPolizas = onPolizas,
                onSiniestros = onSiniestros,
                onPagos = onPagos,
                seleccionada = null
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            val detalle = seccion
            if (detalle != null) {
                Column(modifier = Modifier.padding(horizontal = 20.dp)) {
                    DetallePerfil(
                        seccion = detalle,
                        perfil = perfil,
                        biometriaActivada = biometriaActivada,
                        sinConexion = sinConexion,
                        notificaciones = notificaciones,
                        onCambiarPush = onCambiarPush,
                        onSolicitarPermisoNotificaciones = onSolicitarPermisoNotificaciones,
                        onAbrirAjustesNotificaciones = onAbrirAjustesNotificaciones,
                        onVolver = { seccion = null }
                    )
                }
                return@Column
            }

            Encabezado(titulo = tr(R.string.home_perfil), onVolver = onInicio)
            Column(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                CabeceraPerfil(perfil)
                Text(
                    "MI CUENTA",
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f)
                )

                OpcionPerfil(
                    tr(R.string.profile_datos_personales),
                    tr(R.string.profile_documento_correo_y_celular),
                    Icons.Outlined.PersonOutline
                ) { seccion = SeccionPerfil.CUENTA }
                OpcionPerfil(
                    tr(R.string.profile_seguridad_y_privacidad),
                    textoSeguridad(biometriaActivada, sinConexion),
                    Icons.Outlined.Shield
                ) { seccion = SeccionPerfil.SEGURIDAD }
                OpcionPerfil(
                    tr(R.string.profile_idioma_y_moneda),
                    tr(R.string.profile_idioma_resumen, nombreIdioma(Idioma.actual)),
                    Icons.Outlined.Language
                ) { seccion = SeccionPerfil.IDIOMA }
                OpcionPerfil(
                    tr(R.string.home_notificaciones),
                    textoNotificaciones(notificaciones),
                    Icons.Outlined.NotificationsNone,
                    habilitada = notificaciones != null
                ) { seccion = SeccionPerfil.NOTIFICACIONES }

                TextButton(
                    onClick = onCerrarSesion,
                    enabled = !cerrandoSesion,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.AutoMirrored.Outlined.Logout, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text(if (cerrandoSesion) tr(R.string.advisor_home_cerrando_sesion) else tr(R.string.advisor_home_cerrar_sesion))
                }
            }
        }
    }
}

@Composable
private fun CabeceraPerfil(perfil: Perfil) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(22.dp),
        color = Noche
    ) {
        Row(Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(modifier = Modifier.size(60.dp), shape = CircleShape, color = Avance) {
                Box(contentAlignment = Alignment.Center) {
                    Text(iniciales(perfil), fontWeight = FontWeight.Bold, color = Noche)
                }
            }
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    nombreRol(perfil.rol),
                    style = MaterialTheme.typography.titleMedium,
                    color = Color.White
                )
                Text(
                    "${perfil.nombre} ${perfil.apellido}",
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    perfil.email,
                    color = Color.White.copy(alpha = 0.72f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}

@Composable
private fun OpcionPerfil(
    titulo: String,
    subtitulo: String,
    icono: ImageVector,
    habilitada: Boolean = true,
    onClick: () -> Unit = {}
) {
    Surface(
        onClick = onClick,
        enabled = habilitada,
        modifier = Modifier
            .fillMaxWidth()
            .semantics { if (!habilitada) disabled() }
            .alpha(if (habilitada) 1f else 0.45f),
        shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.surfaceContainer
    ) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(shape = RoundedCornerShape(13.dp), color = Navegacion.copy(alpha = 0.1f)) {
                Icon(
                    icono,
                    contentDescription = null,
                    tint = Navegacion,
                    modifier = Modifier.padding(10.dp).size(22.dp)
                )
            }
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(titulo, fontWeight = FontWeight.Bold)
                Text(
                    subtitulo,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                )
            }
            if (habilitada) {
                Icon(
                    Icons.AutoMirrored.Outlined.KeyboardArrowRight,
                    contentDescription = tr(R.string.profile_abrir, titulo)
                )
            }
        }
    }
}

private enum class SeccionPerfil { CUENTA, SEGURIDAD, IDIOMA, NOTIFICACIONES }

/**
 * Lo que la sección de notificaciones necesita mostrar (HU05). [pushHabilitado] es null mientras se
 * consulta; [permisoConcedido] es el permiso del sistema para mostrar avisos (Android 13 o más).
 */
data class PreferenciasNotificacionesUi(
    val pushHabilitado: Boolean?,
    val guardando: Boolean = false,
    val error: String? = null,
    val permisoConcedido: Boolean = true
)

@Composable
private fun DetallePerfil(
    seccion: SeccionPerfil,
    perfil: Perfil,
    biometriaActivada: Boolean,
    sinConexion: Boolean,
    notificaciones: PreferenciasNotificacionesUi?,
    onCambiarPush: (Boolean) -> Unit,
    onSolicitarPermisoNotificaciones: () -> Unit,
    onAbrirAjustesNotificaciones: () -> Unit,
    onVolver: () -> Unit
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        IconButton(onClick = onVolver) {
            Icon(Icons.AutoMirrored.Outlined.ArrowBack, contentDescription = tr(R.string.profile_volver_al_perfil))
        }
        Text(
            when (seccion) {
                SeccionPerfil.CUENTA -> tr(R.string.profile_datos_personales)
                SeccionPerfil.SEGURIDAD -> tr(R.string.profile_seguridad_y_privacidad)
                SeccionPerfil.IDIOMA -> tr(R.string.profile_idioma_y_moneda)
                SeccionPerfil.NOTIFICACIONES -> tr(R.string.home_notificaciones)
            },
            style = MaterialTheme.typography.titleLarge
        )
    }

    when (seccion) {
        SeccionPerfil.CUENTA -> {
            CampoPerfil(tr(R.string.profile_nombre_completo), "${perfil.nombre} ${perfil.apellido}")
            CampoPerfil(tr(R.string.credentials_login_correo_electronico), perfil.email)
            CampoPerfil(tr(R.string.profile_documento_de_identidad), documento(perfil))
            CampoPerfil(tr(R.string.profile_telefono), perfil.celular?.takeIf(String::isNotBlank) ?: tr(R.string.profile_no_disponible))
        }
        SeccionPerfil.SEGURIDAD -> {
            CampoPerfil(tr(R.string.profile_acceso_biometrico), if (biometriaActivada) tr(R.string.profile_activado) else tr(R.string.profile_no_activado))
            CampoPerfil(tr(R.string.profile_datos_de_polizas), if (sinConexion) tr(R.string.profile_disponibles_sin_conexion) else tr(R.string.profile_copia_local_cifrada))
        }
        SeccionPerfil.IDIOMA -> {
            SelectorIdioma()
            CampoPerfil(tr(R.string.profile_moneda), tr(R.string.profile_peso_colombiano_cop))
        }
        SeccionPerfil.NOTIFICACIONES -> SeccionNotificaciones(
            notificaciones = notificaciones,
            onCambiarPush = onCambiarPush,
            onSolicitarPermiso = onSolicitarPermisoNotificaciones,
            onAbrirAjustes = onAbrirAjustesNotificaciones
        )
    }
}

@Composable
private fun SeccionNotificaciones(
    notificaciones: PreferenciasNotificacionesUi?,
    onCambiarPush: (Boolean) -> Unit,
    onSolicitarPermiso: () -> Unit,
    onAbrirAjustes: () -> Unit
) {
    val preferencia = notificaciones ?: return
    val habilitado = preferencia.pushHabilitado == true
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surfaceContainer
    ) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(tr(R.string.profile_recibir_notificaciones_push), fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(4.dp))
                Text(
                    tr(R.string.profile_avisos_de_pagos_de_tu) +
                        tr(R.string.profile_en_tus_siniestros_siempre_los),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            }
            Spacer(Modifier.width(12.dp))
            Switch(
                checked = habilitado,
                enabled = preferencia.pushHabilitado != null && !preferencia.guardando,
                onCheckedChange = { activar ->
                    onCambiarPush(activar)
                    // El permiso se pide en el momento en que el cliente quiere los avisos.
                    if (activar && !preferencia.permisoConcedido) onSolicitarPermiso()
                },
                modifier = Modifier.semantics { contentDescription = tr(R.string.profile_recibir_notificaciones_push) }
            )
        }
    }
    preferencia.error?.let {
        Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium)
    }
    if (habilitado && !preferencia.permisoConcedido) {
        Surface(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            color = MaterialTheme.colorScheme.errorContainer
        ) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    tr(R.string.profile_las_notificaciones_estan_bloqueadas_en) +
                        tr(R.string.profile_los_avisos_como_notificacion),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onErrorContainer
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    TextButton(onClick = onSolicitarPermiso) { Text(tr(R.string.profile_permitir)) }
                    TextButton(onClick = onAbrirAjustes) { Text(tr(R.string.profile_abrir_ajustes)) }
                }
            }
        }
    }
}

private fun textoNotificaciones(notificaciones: PreferenciasNotificacionesUi?): String = when {
    notificaciones == null -> tr(R.string.profile_disponible_proximamente)
    notificaciones.pushHabilitado == null -> tr(R.string.profile_avisos_de_pagos_siniestros_y)
    notificaciones.pushHabilitado -> tr(R.string.profile_notificaciones_push_activadas)
    else -> tr(R.string.profile_push_desactivado_los_avisos_se)
}

/** Selector del idioma de la app; al elegir otro, la actividad se recrea en ese idioma. */
@Composable
private fun SelectorIdioma() {
    val actividad = LocalContext.current.buscarActividad()
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surfaceContainer
    ) {
        Column(Modifier.padding(16.dp).selectableGroup()) {
            Text(tr(R.string.profile_idioma), style = MaterialTheme.typography.labelMedium)
            Spacer(Modifier.height(4.dp))
            Idioma.Opcion.entries.forEach { opcion ->
                val seleccionado = opcion == Idioma.actual
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .selectable(
                            selected = seleccionado,
                            role = Role.RadioButton,
                            onClick = { actividad?.let { Idioma.cambiar(it, opcion) } }
                        )
                        .padding(vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    RadioButton(selected = seleccionado, onClick = null)
                    Spacer(Modifier.width(12.dp))
                    Text(nombreIdioma(opcion), fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}

/** Nombre de cada idioma en su propio idioma, para reconocerlo aunque no se entienda el actual. */
private fun nombreIdioma(opcion: Idioma.Opcion): String = when (opcion) {
    Idioma.Opcion.ESPANOL -> tr(R.string.idioma_espanol)
    Idioma.Opcion.INGLES -> tr(R.string.idioma_ingles)
}

private tailrec fun Context.buscarActividad(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.buscarActividad()
    else -> null
}

@Composable
private fun CampoPerfil(etiqueta: String, valor: String) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surfaceContainer
    ) {
        Column(Modifier.padding(16.dp)) {
            Text(etiqueta, style = MaterialTheme.typography.labelMedium)
            Spacer(Modifier.height(4.dp))
            Text(valor, fontWeight = FontWeight.SemiBold)
        }
    }
}

private fun iniciales(perfil: Perfil) =
    listOfNotNull(perfil.nombre.firstOrNull(), perfil.apellido.firstOrNull())
        .joinToString("").uppercase()

private fun nombreRol(rol: String) = rol.split('_').joinToString(" ") {
    it.lowercase().replaceFirstChar(Char::uppercase)
}

private fun documento(perfil: Perfil) = listOfNotNull(
    perfil.tipoDocumento?.takeIf(String::isNotBlank),
    perfil.numeroDocumento?.takeIf(String::isNotBlank)
).joinToString(" ").ifBlank { tr(R.string.profile_no_disponible) }

private fun textoSeguridad(biometria: Boolean, sinConexion: Boolean): String = tr(
    R.string.profile_seguridad_resumen,
    if (biometria) tr(R.string.profile_biometria_activa) else tr(R.string.profile_biometria_no_activada),
    if (sinConexion) tr(R.string.profile_datos_offline_disponibles) else tr(R.string.profile_datos_offline_cifrados)
)
