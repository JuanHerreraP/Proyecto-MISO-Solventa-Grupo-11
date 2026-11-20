package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import com.example.solventa.domain.asistencias.Asistencia
import com.example.solventa.domain.asistencias.EstadoAsistencia
import com.example.solventa.domain.asistencias.EstadoAsistencias
import com.example.solventa.domain.asistencias.PasoAsistencia
import com.example.solventa.domain.asistencias.PrestadorCercano
import com.example.solventa.domain.asistencias.PrestadorResumen
import com.example.solventa.domain.asistencias.ServicioAsistencia
import com.example.solventa.domain.asistencias.TipoServicio
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class AssistanceScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private val eventos = mutableListOf<String>()

    private fun mostrar(
        estado: EstadoAsistencias,
        polizas: List<PolizaAsistenciaElegible> = listOf(
            PolizaAsistenciaElegible("POL-1", "Protección de dispositivos · SOL-DP-1")
        ),
        tienePermiso: Boolean = true
    ) {
        compose.setContent {
            SolventaTheme {
                AssistanceScreen(
                    estado = estado,
                    polizasElegibles = polizas,
                    tienePermisoUbicacion = tienePermiso,
                    onSeleccionarPoliza = { eventos += "poliza:${it.polizaId}" },
                    onSeleccionarServicio = { eventos += "servicio:${it.codigo}" },
                    onSolicitarPermiso = { eventos += "permiso" },
                    onBuscarPrestadores = { eventos += "buscar:$it" },
                    onSeleccionarPrestador = { eventos += "prestador:${it.prestadorId}" },
                    onConfirmarSolicitud = { eventos += "confirmar:${it ?: ""}" },
                    onVerMisAsistencias = { eventos += "misAsistencias" },
                    onCancelarAsistencia = { eventos += "cancelar:$it" },
                    onNuevaSolicitud = { eventos += "nueva" },
                    onVolver = { eventos += "volver" }
                )
            }
        }
    }

    private fun servicio(codigo: TipoServicio) = ServicioAsistencia(codigo, codigo.etiqueta)

    private fun prestador(id: String, nombre: String, distancia: Double) = PrestadorCercano(
        prestadorId = id,
        nombre = nombre,
        tipoServicio = TipoServicio.REPARACION_DISPOSITIVO,
        direccion = "Dirección de demostración",
        telefono = "3000000001",
        latitud = 4.715,
        longitud = -74.069,
        distanciaKm = distancia
    )

    @Test
    fun seleccionDePolizaMuestraLaPolizaYNotifica() {
        mostrar(EstadoAsistencias(paso = PasoAsistencia.SELECCION_POLIZA))
        compose.onNodeWithText("Protección de dispositivos · SOL-DP-1").assertIsDisplayed()
        compose.onNodeWithText("Seleccionar").performClick()
        assertEquals(listOf("poliza:POL-1"), eventos)
    }

    @Test
    fun seleccionDeServicioMuestraLasOpcionesYNotifica() {
        mostrar(
            EstadoAsistencias(
                paso = PasoAsistencia.SELECCION_SERVICIO,
                servicios = listOf(
                    servicio(TipoServicio.DIAGNOSTICO_TECNICO),
                    servicio(TipoServicio.REPARACION_DISPOSITIVO)
                )
            )
        )
        compose.onNodeWithText("Diagnóstico técnico").assertIsDisplayed()
        compose.onNodeWithText("Reparación de dispositivo").performClick()
        assertTrue(eventos.contains("servicio:REPARACION_DISPOSITIVO"))
    }

    @Test
    fun permisoDenegadoOfreceReintentar() {
        mostrar(
            EstadoAsistencias(paso = PasoAsistencia.PERMISO_UBICACION, permisoDenegado = true),
            tienePermiso = false
        )
        compose.onNodeWithText("Reintentar").performClick()
        assertEquals(listOf("permiso"), eventos)
    }

    @Test
    fun loadingDePrestadoresMuestraIndicador() {
        mostrar(EstadoAsistencias(paso = PasoAsistencia.PRESTADORES, cargando = true))
        compose.onNodeWithText("Prestadores cercanos").assertIsDisplayed()
    }

    @Test
    fun listaVaciaDePrestadoresPermiteReintentarYAmpliarRadio() {
        mostrar(
            EstadoAsistencias(
                paso = PasoAsistencia.PRESTADORES,
                prestadores = emptyList(),
                radioKm = 25.0
            )
        )
        compose.onNodeWithText("Reintentar").assertIsDisplayed()
        compose.onNodeWithText("Ampliar a 50 km").performClick()
        assertEquals(listOf("buscar:50.0"), eventos)
    }

    @Test
    fun listaDePrestadoresSinUbicacionMuestraLaListaSinMapa() {
        // ubicacion = null: MapaPrestadores no dibuja el GoogleMap, pero la lista sí aparece.
        mostrar(
            EstadoAsistencias(
                paso = PasoAsistencia.PRESTADORES,
                ubicacion = null,
                prestadores = listOf(
                    prestador("PREST-TEC-001", "Solventa Tech Centro", 0.5),
                    prestador("PREST-TEC-002", "TechCare Norte", 1.8)
                )
            )
        )
        compose.onNodeWithText("Solventa Tech Centro").assertIsDisplayed()
        compose.onNodeWithText("TechCare Norte").assertIsDisplayed()
        compose.onAllNodesWithText("Seleccionar")[0].performClick()
        assertTrue(eventos.contains("prestador:PREST-TEC-001"))
    }

    @Test
    fun confirmacionMuestraResumenYEnviaObservaciones() {
        mostrar(
            EstadoAsistencias(
                paso = PasoAsistencia.CONFIRMACION,
                polizaSeleccionadaEtiqueta = "Protección de dispositivos · SOL-DP-1",
                servicioSeleccionado = servicio(TipoServicio.REPARACION_DISPOSITIVO),
                prestadorSeleccionado = prestador("PREST-TEC-001", "Solventa Tech Centro", 0.5),
                ubicacion = com.example.solventa.domain.siniestros.Ubicacion(4.711, -74.072)
            )
        )
        compose.onNodeWithText("Solventa Tech Centro").assertIsDisplayed()
        compose.onNodeWithText("Observaciones (opcional)").performTextInput("No enciende")
        compose.onNodeWithText("Solicitar asistencia").performClick()
        assertTrue(eventos.any { it.startsWith("confirmar:") })
    }

    @Test
    fun exitoMuestraLaSolicitudYNavega() {
        mostrar(
            EstadoAsistencias(
                paso = PasoAsistencia.EXITO,
                asistenciaCreada = Asistencia(
                    asistenciaId = "ASI-1",
                    polizaId = "POL-1",
                    prestador = PrestadorResumen("PREST-TEC-001", "Solventa Tech Centro", "3000000001"),
                    servicio = TipoServicio.REPARACION_DISPOSITIVO,
                    estado = EstadoAsistencia.SOLICITADA,
                    latitud = 4.711,
                    longitud = -74.072,
                    observaciones = null,
                    creadaEn = "2026-11-15T14:30:00Z",
                    canceladaEn = null
                )
            )
        )
        compose.onNodeWithText("ASI-1").assertIsDisplayed()
        compose.onNodeWithText("Ver mis asistencias").performClick()
        assertEquals(listOf("misAsistencias"), eventos)
    }

    @Test
    fun misAsistenciasMuestraSolicitadaYPermiteCancelar() {
        mostrar(
            EstadoAsistencias(
                paso = PasoAsistencia.MIS_ASISTENCIAS,
                asistencias = listOf(
                    Asistencia(
                        asistenciaId = "ASI-1",
                        polizaId = "POL-1",
                        prestador = PrestadorResumen("PREST-TEC-001", "Solventa Tech Centro", null),
                        servicio = TipoServicio.REPARACION_DISPOSITIVO,
                        estado = EstadoAsistencia.SOLICITADA,
                        latitud = 4.711,
                        longitud = -74.072,
                        observaciones = null,
                        creadaEn = "2026-11-15T14:30:00Z",
                        canceladaEn = null
                    )
                )
            )
        )
        compose.onNodeWithText("Solventa Tech Centro").assertIsDisplayed()
        compose.onNodeWithText("Solicitada").assertIsDisplayed()
        compose.onNodeWithText("Cancelar asistencia").performClick()
        assertEquals(listOf("cancelar:ASI-1"), eventos)
    }

    @Test
    fun asistenciaCanceladaNoMuestraBotonDeCancelar() {
        mostrar(
            EstadoAsistencias(
                paso = PasoAsistencia.MIS_ASISTENCIAS,
                asistencias = listOf(
                    Asistencia(
                        asistenciaId = "ASI-1",
                        polizaId = "POL-1",
                        prestador = PrestadorResumen("PREST-TEC-001", "Solventa Tech Centro", null),
                        servicio = TipoServicio.REPARACION_DISPOSITIVO,
                        estado = EstadoAsistencia.CANCELADA,
                        latitud = 4.711,
                        longitud = -74.072,
                        observaciones = null,
                        creadaEn = "2026-11-15T14:30:00Z",
                        canceladaEn = "2026-11-15T15:00:00Z"
                    )
                )
            )
        )
        compose.onNodeWithText("Cancelada").assertIsDisplayed()
        compose.onAllNodesWithText("Cancelar asistencia").assertCountEquals(0)
    }

    private fun asistencia(
        estado: EstadoAsistencia,
        eta: Int? = null
    ) = Asistencia(
        asistenciaId = "ASI-1",
        polizaId = "POL-1",
        prestador = PrestadorResumen("PREST-MAD-002", "Centro Técnico Madrid", "3000000000"),
        servicio = TipoServicio.REPARACION_DISPOSITIVO,
        estado = estado,
        latitud = 4.711,
        longitud = -74.072,
        observaciones = null,
        creadaEn = "2026-11-15T14:30:00Z",
        canceladaEn = if (estado == EstadoAsistencia.CANCELADA) "2026-11-15T15:00:00Z" else null,
        aceptadaEn = if (estado == EstadoAsistencia.ACEPTADA) "2026-11-15T15:03:00Z" else null,
        tiempoEstimadoLlegadaMinutos = eta
    )

    @Test
    fun aceptadaConEtaMuestraLosMinutos() {
        mostrar(
            EstadoAsistencias(
                paso = PasoAsistencia.MIS_ASISTENCIAS,
                asistencias = listOf(asistencia(EstadoAsistencia.ACEPTADA, eta = 20))
            )
        )
        compose.onNodeWithText("Aceptada").assertIsDisplayed()
        compose.onNodeWithText("El prestador aceptó tu solicitud.").assertIsDisplayed()
        compose.onNodeWithText("Tiempo estimado de llegada").assertIsDisplayed()
        compose.onNodeWithText("20 min").assertIsDisplayed()
        // Una asistencia aceptada no ofrece cancelar.
        compose.onAllNodesWithText("Cancelar asistencia").assertCountEquals(0)
    }

    @Test
    fun aceptadaSinEtaMuestraAunNoDisponible() {
        mostrar(
            EstadoAsistencias(
                paso = PasoAsistencia.MIS_ASISTENCIAS,
                asistencias = listOf(asistencia(EstadoAsistencia.ACEPTADA, eta = null))
            )
        )
        compose.onNodeWithText("Aceptada").assertIsDisplayed()
        compose.onNodeWithText("Tiempo estimado de llegada").assertIsDisplayed()
        compose.onNodeWithText("Aún no disponible").assertIsDisplayed()
        compose.onAllNodesWithText("0 min").assertCountEquals(0)
    }
}
