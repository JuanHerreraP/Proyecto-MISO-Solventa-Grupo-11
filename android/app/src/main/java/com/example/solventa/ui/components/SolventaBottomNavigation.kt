package com.example.solventa.ui.components

import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Payments
import androidx.compose.material.icons.outlined.Policy
import androidx.compose.material.icons.outlined.RequestQuote
import androidx.compose.material.icons.outlined.WarningAmber
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.Noche

enum class SeccionNavegacion {
    INICIO,
    COTIZACIONES,
    POLIZAS,
    SINIESTROS,
    PAGOS
}

@Composable
fun SolventaBottomNavigation(
    onInicio: () -> Unit = {},
    onCotizaciones: (() -> Unit)? = null,
    onPolizas: (() -> Unit)? = null,
    onSiniestros: (() -> Unit)? = null,
    onPagos: (() -> Unit)? = null,
    seleccionada: SeccionNavegacion? = SeccionNavegacion.INICIO
) {
    val colores = NavigationBarItemDefaults.colors(
        selectedIconColor = Navegacion,
        selectedTextColor = Navegacion,
        indicatorColor = Navegacion.copy(alpha = 0.12f),
        unselectedIconColor = Noche.copy(alpha = 0.65f),
        unselectedTextColor = Noche.copy(alpha = 0.65f),
        disabledIconColor = Noche.copy(alpha = 0.35f),
        disabledTextColor = Noche.copy(alpha = 0.35f)
    )

    NavigationBar(
        containerColor = MaterialTheme.colorScheme.surfaceContainer,
        windowInsets = WindowInsets(0, 0, 0, 0)
    ) {
        NavigationBarItem(
            selected = seleccionada == SeccionNavegacion.INICIO,
            onClick = onInicio,
            icon = { Icon(Icons.Outlined.Home, contentDescription = null) },
            label = { Text("Inicio") },
            colors = colores
        )
        NavigationBarItem(
            selected = seleccionada == SeccionNavegacion.COTIZACIONES,
            onClick = { onCotizaciones?.invoke() },
            enabled = onCotizaciones != null || seleccionada == SeccionNavegacion.COTIZACIONES,
            icon = { Icon(Icons.Outlined.RequestQuote, contentDescription = null) },
            label = { Text("Cotizaciones") },
            colors = colores
        )
        NavigationBarItem(
            selected = seleccionada == SeccionNavegacion.POLIZAS,
            onClick = { onPolizas?.invoke() },
            enabled = onPolizas != null || seleccionada == SeccionNavegacion.POLIZAS,
            icon = { Icon(Icons.Outlined.Policy, contentDescription = null) },
            label = { Text("Pólizas") },
            colors = colores
        )
        NavigationBarItem(
            selected = seleccionada == SeccionNavegacion.SINIESTROS,
            onClick = { onSiniestros?.invoke() },
            enabled = onSiniestros != null || seleccionada == SeccionNavegacion.SINIESTROS,
            icon = { Icon(Icons.Outlined.WarningAmber, contentDescription = null) },
            label = { Text("Siniestros") },
            colors = colores
        )
        NavigationBarItem(
            selected = seleccionada == SeccionNavegacion.PAGOS,
            onClick = { onPagos?.invoke() },
            enabled = onPagos != null || seleccionada == SeccionNavegacion.PAGOS,
            icon = { Icon(Icons.Outlined.Payments, contentDescription = null) },
            label = { Text("Pagos") },
            colors = colores
        )
    }
}
