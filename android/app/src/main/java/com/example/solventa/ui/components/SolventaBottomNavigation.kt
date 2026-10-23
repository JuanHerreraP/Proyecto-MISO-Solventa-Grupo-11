package com.example.solventa.ui.components

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.PersonOutline
import androidx.compose.material.icons.outlined.Policy
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import com.example.solventa.ui.theme.Navegacion
import com.example.solventa.ui.theme.Noche

@Composable
fun SolventaBottomNavigation(
    onInicio: () -> Unit = {},
    onPolizas: (() -> Unit)? = null
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

    NavigationBar(containerColor = MaterialTheme.colorScheme.surface) {
        NavigationBarItem(
            selected = true,
            onClick = onInicio,
            icon = { Icon(Icons.Outlined.Home, contentDescription = null) },
            label = { Text("Inicio") },
            colors = colores
        )
        NavigationBarItem(
            selected = false,
            onClick = { onPolizas?.invoke() },
            enabled = onPolizas != null,
            icon = { Icon(Icons.Outlined.Policy, contentDescription = null) },
            label = { Text("Pólizas") },
            colors = colores
        )
        NavigationBarItem(
            selected = false,
            onClick = {},
            icon = { Icon(Icons.Outlined.Description, contentDescription = null) },
            label = { Text("Siniestros") },
            colors = colores
        )
        NavigationBarItem(
            selected = false,
            onClick = {},
            icon = { Icon(Icons.Outlined.PersonOutline, contentDescription = null) },
            label = { Text("Perfil") },
            colors = colores
        )
    }
}
