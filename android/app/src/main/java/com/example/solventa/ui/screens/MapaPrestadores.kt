package com.example.solventa.ui.screens

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import com.example.solventa.domain.asistencias.EstadoAsistencias
import com.google.android.gms.maps.model.CameraPosition
import com.google.android.gms.maps.model.LatLng
import com.google.maps.android.compose.GoogleMap
import com.google.maps.android.compose.MapProperties
import com.google.maps.android.compose.MapUiSettings
import com.google.maps.android.compose.Marker
import com.google.maps.android.compose.MarkerState
import com.google.maps.android.compose.rememberCameraPositionState
import com.google.maps.android.compose.rememberMarkerState

/**
 * Mapa con la ubicación del cliente y los prestadores cercanos (HU06).
 *
 * Está aislado del resto de la pantalla a propósito: así `AssistanceScreen` se puede probar con
 * Robolectric (que no renderiza el mapa) ejercitando la lista y el resto del flujo. El mapa no
 * llama a APIs externas en pruebas unitarias.
 *
 * El [modifier] que llega trae una **altura fija** (lo invoca `AssistanceScreen` con
 * `fillMaxWidth().height(220.dp)`). Esa altura se le pasa directamente al `GoogleMap`: dentro de
 * una columna con scroll vertical, envolverlo en un `Box` con `fillMaxSize` dejaba la vista nativa
 * del mapa sin alto estable y los mosaicos no se dibujaban (mapa en blanco con logo y zoom).
 */
@Composable
fun MapaPrestadores(
    estado: EstadoAsistencias,
    modifier: Modifier = Modifier
) {
    val ubicacion = estado.ubicacion ?: return
    val centro = LatLng(ubicacion.latitud, ubicacion.longitud)
    val camara = rememberCameraPositionState {
        position = CameraPosition.fromLatLngZoom(centro, 13f)
    }
    val miUbicacion = rememberMarkerState(position = centro)

    GoogleMap(
        modifier = modifier.clip(RoundedCornerShape(16.dp)),
        cameraPositionState = camara,
        properties = remember { MapProperties() },
        uiSettings = remember {
            MapUiSettings(zoomControlsEnabled = true, zoomGesturesEnabled = true)
        }
    ) {
        Marker(state = miUbicacion, title = "Mi ubicación")
        estado.prestadores.forEach { prestador ->
            Marker(
                state = MarkerState(position = LatLng(prestador.latitud, prestador.longitud)),
                title = prestador.nombre,
                snippet = "${prestador.tipoServicio.etiqueta} · ${formatoKm(prestador.distanciaKm)}"
            )
        }
    }
}
