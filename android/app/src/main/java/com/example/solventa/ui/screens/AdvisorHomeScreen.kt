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
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Logout
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.outlined.PersonAdd
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.asesor.ClienteDeAsesor
import com.example.solventa.ui.components.SolventaPrimaryButton
import com.example.solventa.ui.components.SolventaTextField
import com.example.solventa.ui.theme.Atencion
import com.example.solventa.ui.theme.Avance
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.SolventaTheme

/**
 * Inicio del asesor de ventas (HU20): lista los clientes que atiende, permite asociar nuevos
 * y, al elegir uno, abrir el registro de un siniestro en su nombre.
 */
@Composable
fun AdvisorHomeScreen(
    nombre: String,
    clientes: List<ClienteDeAsesor>,
    cargando: Boolean,
    error: String?,
    asociando: Boolean,
    errorAsociar: String?,
    avisoAsociado: String?,
    cerrandoSesion: Boolean,
    onAsociarCliente: (String) -> Unit,
    onRegistrarSiniestro: (ClienteDeAsesor) -> Unit,
    onCerrarSesion: () -> Unit,
    modifier: Modifier = Modifier,
    puedeCrearAsesor: Boolean = false,
    onCrearAsesor: () -> Unit = {}
) {
    var email by remember { mutableStateOf("") }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets(0, 0, 0, 0)
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Outlined.Shield,
                    contentDescription = null,
                    modifier = Modifier.size(24.dp),
                    tint = Navegacion
                )
                Spacer(modifier = Modifier.width(10.dp))
                Text(
                    text = "Solventa · Asesor",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }

            Text(
                text = "Hola, $nombre",
                style = MaterialTheme.typography.headlineLarge,
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = "Gestiona tus clientes y registra siniestros en su nombre.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
            )

            if (puedeCrearAsesor) {
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
                        Icon(Icons.Outlined.PersonAdd, contentDescription = null, tint = Navegacion)
                        Spacer(modifier = Modifier.width(12.dp))
                        Text(
                            text = "Crear un asesor de ventas",
                            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                            color = MaterialTheme.colorScheme.onSurface,
                            modifier = Modifier.weight(1f)
                        )
                        Icon(Icons.Filled.ChevronRight, contentDescription = null, tint = Navegacion)
                    }
                }
            }

            // Bloque: asociar un cliente por correo.
            Surface(
                shape = RoundedCornerShape(18.dp),
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text(
                        text = "Asociar un cliente",
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    SolventaTextField(
                        value = email,
                        onValueChange = { email = it },
                        label = "Correo del cliente",
                        placeholder = "cliente@correo.com"
                    )
                    if (errorAsociar != null) {
                        Text(text = errorAsociar, style = MaterialTheme.typography.bodyMedium, color = Atencion)
                    }
                    if (avisoAsociado != null) {
                        Text(text = avisoAsociado, style = MaterialTheme.typography.bodyMedium, color = Avance)
                    }
                    SolventaPrimaryButton(
                        text = "Asociar cliente",
                        onClick = {
                            if (email.isNotBlank()) {
                                onAsociarCliente(email.trim())
                                email = ""
                            }
                        },
                        enabled = !asociando && email.isNotBlank(),
                        isLoading = asociando
                    )
                }
            }

            Text(
                text = "Mis clientes",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurface
            )

            when {
                cargando && clientes.isEmpty() -> Box(
                    modifier = Modifier.fillMaxWidth().padding(24.dp),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(
                        color = Navegacion,
                        modifier = Modifier.semantics { contentDescription = "Cargando tus clientes" }
                    )
                }

                error != null && clientes.isEmpty() ->
                    Text(text = error, style = MaterialTheme.typography.bodyMedium, color = Atencion)

                clientes.isEmpty() ->
                    Text(
                        text = "Aún no tienes clientes asociados.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                    )

                else -> clientes.forEach { cliente ->
                    TarjetaCliente(cliente = cliente, onRegistrar = { onRegistrarSiniestro(cliente) })
                }
            }

            Spacer(modifier = Modifier.size(8.dp))
            TextButton(
                onClick = onCerrarSesion,
                enabled = !cerrandoSesion,
                modifier = Modifier.align(Alignment.CenterHorizontally)
            ) {
                Icon(Icons.AutoMirrored.Outlined.Logout, contentDescription = null, tint = Navegacion)
                Spacer(modifier = Modifier.width(8.dp))
                Text(if (cerrandoSesion) "Cerrando sesión…" else "Cerrar sesión", color = Navegacion)
            }
            Spacer(modifier = Modifier.size(24.dp))
        }
    }
}

@Composable
private fun TarjetaCliente(cliente: ClienteDeAsesor, onRegistrar: () -> Unit) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.04f),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(role = Role.Button, onClickLabel = "Registrar siniestro", onClick = onRegistrar)
    ) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    text = cliente.nombreCompleto,
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Text(
                    text = cliente.email,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
                Text(
                    text = "Registrar siniestro",
                    style = MaterialTheme.typography.labelMedium,
                    color = Navegacion
                )
            }
            Icon(
                imageVector = Icons.Filled.ChevronRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)
            )
        }
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun AdvisorHomeScreenPreview() {
    SolventaTheme {
        AdvisorHomeScreen(
            nombre = "María",
            clientes = listOf(
                ClienteDeAsesor("c1", "Ana", "Pérez", "ana@gmail.com"),
                ClienteDeAsesor("c2", "Luis", "Gómez", "luis@gmail.com")
            ),
            cargando = false,
            error = null,
            asociando = false,
            errorAsociar = null,
            avisoAsociado = null,
            cerrandoSesion = false,
            onAsociarCliente = {},
            onRegistrarSiniestro = {},
            onCerrarSesion = {},
            puedeCrearAsesor = false
        )
    }
}
