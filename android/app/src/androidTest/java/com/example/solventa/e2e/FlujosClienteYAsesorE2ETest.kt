package com.example.solventa.e2e

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.solventa.E2ETestActivity
import com.example.solventa.domain.asesor.ClienteDeAsesor
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.example.solventa.domain.pagos.PrimaPendiente
import com.example.solventa.domain.pagos.TipoPrimaPendiente
import com.example.solventa.domain.polizas.Billetera
import com.example.solventa.domain.polizas.CategoriaMovimiento
import com.example.solventa.domain.polizas.EstadoPoliza
import com.example.solventa.domain.polizas.HistorialPoliza
import com.example.solventa.domain.polizas.MovimientoPoliza
import com.example.solventa.domain.polizas.NaturalezaMonto
import com.example.solventa.domain.polizas.PolizaResumen
import com.example.solventa.domain.polizas.TipoMovimiento
import com.example.solventa.domain.siniestros.EstadoSiniestro
import com.example.solventa.domain.siniestros.OrigenSiniestro
import com.example.solventa.domain.siniestros.Siniestro
import com.example.solventa.domain.siniestros.Siniestros
import com.example.solventa.ui.cotizaciones.CotizacionDemostracion
import com.example.solventa.ui.screens.AdvisorHomeScreen
import com.example.solventa.ui.screens.ClaimDetailScreen
import com.example.solventa.ui.screens.ClaimsScreen
import com.example.solventa.ui.screens.PaymentScreen
import com.example.solventa.ui.screens.PaymentsScreen
import com.example.solventa.ui.screens.PolicyHistoryScreen
import com.example.solventa.ui.screens.QuoteResultScreen
import com.example.solventa.ui.screens.QuotesScreen
import com.example.solventa.ui.screens.WalletScreen
import com.example.solventa.ui.theme.SolventaTheme
import java.math.BigDecimal
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Recorridos instrumentados de los módulos disponibles para cliente y asesor.
 * Cada recorrido usa datos controlados en el dispositivo: no necesita Docker ni modifica backend.
 */
@RunWith(AndroidJUnit4::class)
class FlujosClienteYAsesorE2ETest {
    @get:Rule
    val compose = createAndroidComposeRule<E2ETestActivity>()

    @Test
    fun cotizacionDelClienteAbreSuDetalle() {
        val cotizacion = CotizacionDemostracion.para(RamoCotizacion.VIAJE)
        var detalleAbierto by mutableStateOf(false)

        compose.setContent {
            SolventaTheme {
                if (detalleAbierto) {
                    QuoteResultScreen(
                        cotizacion = cotizacion,
                        onVolver = { detalleAbierto = false },
                        onAceptar = {},
                        onCrearOtra = {},
                        modoDetalle = true
                    )
                } else {
                    QuotesScreen(
                        cotizaciones = listOf(cotizacion),
                        cargando = false,
                        error = null,
                        onVerCotizacion = { detalleAbierto = true },
                        onReintentar = {},
                        onVolver = {}
                    )
                }
            }
        }

        compose.boton("Seguro de viaje").performClick()

        compose.onNodeWithText("COTIZACIÓN").assertIsDisplayed()
        compose.onNodeWithText("Cerrar").assertIsDisplayed()
    }

    @Test
    fun primaPendienteAbreElFormularioDePago() {
        val pendiente = primaPendiente()
        var solicitudId: String? by mutableStateOf(null)

        compose.setContent {
            SolventaTheme {
                if (solicitudId == null) {
                    PaymentsScreen(
                        pagos = emptyList(),
                        pendientes = listOf(pendiente),
                        cargando = false,
                        error = null,
                        onReintentar = {},
                        onVolver = {},
                        onPagar = { solicitudId = it.cotizacionId }
                    )
                } else {
                    PaymentScreen(
                        cotizacionId = solicitudId.orEmpty(),
                        monto = pendiente.monto,
                        moneda = pendiente.moneda,
                        procesando = false,
                        error = null,
                        onVolver = {},
                        onPagar = {}
                    )
                }
            }
        }

        compose.boton("Pagar").performClick()

        compose.onNodeWithText("PAGO DE LA PRIMA").assertIsDisplayed()
        assertEquals("COT-E2E-1", solicitudId)
    }

    @Test
    fun billeteraOfflineConservaLaPolizaDisponible() {
        var polizaSeleccionada: String? by mutableStateOf(null)

        compose.setContent {
            SolventaTheme {
                WalletScreen(
                    billetera = billetera(),
                    cargando = false,
                    error = null,
                    sinConexion = true,
                    ultimaSincronizacionMs = 1_798_000_000_000L,
                    datosAntiguos = true,
                    onVerPoliza = { polizaSeleccionada = it },
                    onReintentar = {},
                    onVolver = {}
                )
            }
        }

        compose.onNodeWithText("Sin conexión · Última actualización:", substring = true).assertIsDisplayed()
        compose.onNodeWithText("Estos datos tienen más de 30 días", substring = true).assertIsDisplayed()
        compose.boton("Seguro de viaje").performClick()

        assertEquals("POL-E2E-1", polizaSeleccionada)
    }

    @Test
    fun historialDePolizaMuestraMovimientosContractualesYFinancieros() {
        compose.setContent {
            SolventaTheme {
                PolicyHistoryScreen(
                    numeroPoliza = "SOL-E2E-1",
                    nombreRamo = "Seguro de viaje",
                    historial = historial(),
                    cargando = false,
                    error = null,
                    onReintentar = {},
                    onVolver = {}
                )
            }
        }

        compose.onAllNodesWithText("Emisión de póliza").assertCountEquals(2)
        compose.onNodeWithText("Reembolso por prima no devengada").performScrollTo().assertIsDisplayed()
    }

    @Test
    fun clienteAbreElDetalleDeSuSiniestro() {
        val siniestro = siniestro()
        var seleccionado: Siniestro? by mutableStateOf(null)

        compose.setContent {
            SolventaTheme {
                if (seleccionado == null) {
                    ClaimsScreen(
                        siniestros = Siniestros(listOf(siniestro)),
                        cargando = false,
                        error = null,
                        onReintentar = {},
                        onVolver = {},
                        onVerDetalle = { seleccionado = it }
                    )
                } else {
                    ClaimDetailScreen(
                        siniestro = seleccionado,
                        cargando = false,
                        error = null,
                        onReintentar = {},
                        onVolver = { seleccionado = null }
                    )
                }
            }
        }

        compose.boton("Póliza POL-E2E-1").performClick()

        compose.onNodeWithText("Siniestro SIN-E2E-1").assertIsDisplayed()
        compose.onNodeWithText("Progreso del caso").assertIsDisplayed()
    }

    @Test
    fun asesorAsociaUnClientePorCorreo() {
        var aviso: String? by mutableStateOf(null)

        compose.setContent {
            SolventaTheme {
                AdvisorHomeScreen(
                    nombre = "Andrea",
                    clientes = emptyList(),
                    cargando = false,
                    error = null,
                    asociando = false,
                    errorAsociar = null,
                    avisoAsociado = aviso,
                    cerrandoSesion = false,
                    onAsociarCliente = { aviso = "Cliente asociado: $it" },
                    onRegistrarSiniestro = {},
                    onCerrarSesion = {}
                )
            }
        }

        compose.campo("CORREO DEL CLIENTE").performTextInput("cliente@solventa.co")
        compose.boton("Asociar cliente").performClick()

        compose.onNodeWithText("Cliente asociado: cliente@solventa.co").assertIsDisplayed()
    }

    @Test
    fun asesorSeleccionaClienteParaRegistrarSiniestro() {
        val cliente = ClienteDeAsesor("CLI-E2E-1", "Ana", "Pérez", "ana@solventa.co")
        var clienteSeleccionado: ClienteDeAsesor? by mutableStateOf(null)

        compose.setContent {
            SolventaTheme {
                if (clienteSeleccionado == null) {
                    AdvisorHomeScreen(
                        nombre = "Andrea",
                        clientes = listOf(cliente),
                        cargando = false,
                        error = null,
                        asociando = false,
                        errorAsociar = null,
                        avisoAsociado = null,
                        cerrandoSesion = false,
                        onAsociarCliente = {},
                        onRegistrarSiniestro = { clienteSeleccionado = it },
                        onCerrarSesion = {}
                    )
                } else {
                    androidx.compose.material3.Text("Registrar siniestro para ${clienteSeleccionado?.nombreCompleto}")
                }
            }
        }

        compose.boton("Ana Pérez").performClick()

        compose.onNodeWithText("Registrar siniestro para Ana Pérez").assertIsDisplayed()
    }

    @Test
    fun servicioInternoPuedeAbrirLaCreacionDeAsesores() {
        var abrirCreacion by mutableStateOf(false)

        compose.setContent {
            SolventaTheme {
                if (abrirCreacion) {
                    androidx.compose.material3.Text("Crear asesor de ventas")
                } else {
                    AdvisorHomeScreen(
                        nombre = "Operaciones",
                        clientes = emptyList(),
                        cargando = false,
                        error = null,
                        asociando = false,
                        errorAsociar = null,
                        avisoAsociado = null,
                        cerrandoSesion = false,
                        onAsociarCliente = {},
                        onRegistrarSiniestro = {},
                        onCerrarSesion = {},
                        puedeCrearAsesor = true,
                        onCrearAsesor = { abrirCreacion = true }
                    )
                }
            }
        }

        compose.boton("Crear un asesor de ventas").performClick()

        compose.onNodeWithText("Crear asesor de ventas").assertIsDisplayed()
    }
}

private fun androidx.compose.ui.test.SemanticsNodeInteractionsProvider.boton(texto: String) =
    onNode(hasText(texto, substring = false) and hasClickAction())

private fun androidx.compose.ui.test.SemanticsNodeInteractionsProvider.campo(etiqueta: String) =
    onNode(hasSetTextAction() and hasText(etiqueta))

private fun primaPendiente() = PrimaPendiente(
    tipo = TipoPrimaPendiente.COTIZACION,
    referenciaId = "COT-E2E-1",
    cotizacionId = "COT-E2E-1",
    polizaId = null,
    numeroPoliza = null,
    nombreRamo = "Seguro de viaje",
    monto = BigDecimal("84000"),
    moneda = "COP",
    fechaLimite = "2026-12-01T12:00:00Z",
    mensaje = null
)

private fun billetera() = Billetera(
    polizas = listOf(
        PolizaResumen(
            polizaId = "POL-E2E-1",
            numeroPoliza = "SOL-E2E-1",
            ramo = "VIAJE",
            nombreRamo = "Seguro de viaje",
            estado = EstadoPoliza.VIGENTE,
            activa = true,
            fechaInicio = "2026-11-13",
            fechaFin = "2026-11-27",
            coberturaPrincipal = "Asistencia integral de viaje",
            emitidaEn = "2026-11-07T14:07:00Z"
        )
    ),
    totalVigentes = 1,
    totalInactivas = 0
)

private fun historial() = HistorialPoliza(
    polizaId = "POL-E2E-1",
    numeroPoliza = "SOL-E2E-1",
    nombreRamo = "Seguro de viaje",
    estado = "VIGENTE",
    movimientos = listOf(
        MovimientoPoliza(
            movimientoId = "MOV-E2E-1",
            polizaId = "POL-E2E-1",
            categoria = CategoriaMovimiento.POLIZA,
            tipo = TipoMovimiento.EMISION,
            fecha = "2026-11-07T14:07:00Z",
            descripcion = "Emisión de póliza",
            referencia = "SOL-E2E-1",
            referenciaExterna = null,
            estado = "COMPLETADO",
            monto = null,
            moneda = null,
            naturalezaMonto = null,
            cambios = emptyList()
        ),
        MovimientoPoliza(
            movimientoId = "MOV-E2E-2",
            polizaId = "POL-E2E-1",
            categoria = CategoriaMovimiento.FINANCIERO,
            tipo = TipoMovimiento.REEMBOLSO,
            fecha = "2026-11-08T14:07:00Z",
            descripcion = "Reembolso por prima no devengada",
            referencia = "REF-E2E-1",
            referenciaExterna = null,
            estado = "COMPLETADO",
            monto = "10000",
            moneda = "COP",
            naturalezaMonto = NaturalezaMonto.REEMBOLSO,
            cambios = emptyList()
        )
    )
)

private fun siniestro() = Siniestro(
    siniestroId = "SIN-E2E-1",
    polizaId = "POL-E2E-1",
    origen = OrigenSiniestro.MANUAL,
    estado = EstadoSiniestro.EN_EVALUACION,
    eventoId = null,
    fechaEvento = "2026-11-15",
    horaEvento = "10:30:00",
    lugar = "Bogotá",
    descripcion = "Daño durante el viaje",
    estimacionDanos = "250000",
    moneda = "COP",
    registradoEn = "2026-11-15T11:00:00Z"
)
