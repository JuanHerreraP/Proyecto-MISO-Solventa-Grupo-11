package com.example.solventa.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext

// Dark Mode Palette Mapping
private val DarkColorScheme = darkColorScheme(
    primary = Navegacion,
    onPrimary = Color.White,
    secondary = Offline,
    onSecondary = Color.Black,
    tertiary = Avance,
    onTertiary = Color.Black,
    background = Noche,
    onBackground = Color.White,
    surface = Noche,
    onSurface = Color.White
)

// Light Mode Palette Mapping
private val LightColorScheme = lightColorScheme(
    primary = Navegacion,
    onPrimary = Color.White,
    secondary = Offline,
    onSecondary = Color.White,
    tertiary = Avance,
    onTertiary = Noche,
    background = Color(0xFFF8F9FA), // Clean light off-white background
    onBackground = Noche,            // Dark text using Noche
    surface = Color.White,
    onSurface = Noche
)

@Composable
fun SolventaTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    // Set dynamicColor default to false so brand colors remain active
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }

        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}