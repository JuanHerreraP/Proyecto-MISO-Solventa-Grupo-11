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
import com.example.solventa.ui.components.SeccionNavegacion
import com.example.solventa.ui.components.SolventaBottomNavigation
import com.example.solventa.ui.theme.Avance
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.Noche

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
                onPolizas = onPolizas,
                onSiniestros = onSiniestros,
                onPerfil = {},
                seleccionada = SeccionNavegacion.PERFIL
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            val detalle = seccion
            if (detalle != null) {
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
                return@Column
            }

            Text("Perfil", style = MaterialTheme.typography.titleLarge)
            CabeceraPerfil(perfil)
            Text(
                "MI CUENTA",
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f)
            )

            OpcionPerfil(
                "Datos personales",
                "Documento, correo y celular",
                Icons.Outlined.PersonOutline
            ) { seccion = SeccionPerfil.CUENTA }
            OpcionPerfil(
                "Seguridad y privacidad",
                textoSeguridad(biometriaActivada, sinConexion),
                Icons.Outlined.Shield
            ) { seccion = SeccionPerfil.SEGURIDAD }
            OpcionPerfil(
                "Idioma y moneda",
                "Español (Colombia) · Peso colombiano (COP)",
                Icons.Outlined.Language
            ) { seccion = SeccionPerfil.IDIOMA }
            OpcionPerfil(
                "Notificaciones",
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
                Text(if (cerrandoSesion) "Cerrando sesión…" else "Cerrar sesión")
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
                    contentDescription = "Abrir $titulo"
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
            Icon(Icons.AutoMirrored.Outlined.ArrowBack, contentDescription = "Volver al perfil")
        }
        Text(
            when (seccion) {
                SeccionPerfil.CUENTA -> "Datos personales"
                SeccionPerfil.SEGURIDAD -> "Seguridad y privacidad"
                SeccionPerfil.IDIOMA -> "Idioma y moneda"
                SeccionPerfil.NOTIFICACIONES -> "Notificaciones"
            },
            style = MaterialTheme.typography.titleLarge
        )
    }

    when (seccion) {
        SeccionPerfil.CUENTA -> {
            CampoPerfil("Nombre completo", "${perfil.nombre} ${perfil.apellido}")
            CampoPerfil("Correo electrónico", perfil.email)
            CampoPerfil("Documento de identidad", documento(perfil))
            CampoPerfil("Teléfono", perfil.celular?.takeIf(String::isNotBlank) ?: "No disponible")
        }
        SeccionPerfil.SEGURIDAD -> {
            CampoPerfil("Acceso biométrico", if (biometriaActivada) "Activado" else "No activado")
            CampoPerfil("Datos de pólizas", if (sinConexion) "Disponibles sin conexión" else "Copia local cifrada")
        }
        SeccionPerfil.IDIOMA -> {
            CampoPerfil("Idioma", "Español (Colombia)")
            CampoPerfil("Moneda", "Peso colombiano (COP)")
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
                Text("Recibir notificaciones push", fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(4.dp))
                Text(
                    "Avisos de pagos de tu seguro paramétrico, vencimientos de pólizas y cambios " +
                        "en tus siniestros. Siempre los verás también dentro de la app.",
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
                modifier = Modifier.semantics { contentDescription = "Recibir notificaciones push" }
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
                    "Las notificaciones están bloqueadas en tu teléfono. Permítelas para recibir " +
                        "los avisos como notificación.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onErrorContainer
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    TextButton(onClick = onSolicitarPermiso) { Text("Permitir") }
                    TextButton(onClick = onAbrirAjustes) { Text("Abrir ajustes") }
                }
            }
        }
    }
}

private fun textoNotificaciones(notificaciones: PreferenciasNotificacionesUi?): String = when {
    notificaciones == null -> "Disponible próximamente"
    notificaciones.pushHabilitado == null -> "Avisos de pagos, siniestros y vencimientos"
    notificaciones.pushHabilitado -> "Notificaciones push activadas"
    else -> "Push desactivado · los avisos se ven en la app"
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
).joinToString(" ").ifBlank { "No disponible" }

private fun textoSeguridad(biometria: Boolean, sinConexion: Boolean): String =
    "${if (biometria) "Biometría activa" else "Biometría no activada"} · " +
        if (sinConexion) "datos offline disponibles" else "datos offline cifrados"
