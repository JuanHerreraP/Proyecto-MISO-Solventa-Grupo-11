package com.example.solventa.ui.screens

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.example.solventa.domain.auth.Perfil
import com.example.solventa.domain.notificaciones.Bandeja
import com.example.solventa.domain.notificaciones.Notificacion
import com.example.solventa.domain.notificaciones.TipoNotificacion
import com.example.solventa.domain.siniestros.EstadoSiniestro
import com.example.solventa.domain.siniestros.OrigenSiniestro
import com.example.solventa.domain.siniestros.Siniestro
import com.example.solventa.ui.theme.SolventaTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

private fun notificacion(id: String, leida: Boolean, tipo: TipoNotificacion = TipoNotificacion.ESTADO_SINIESTRO) =
    Notificacion(
        id, tipo, "Título $id", "Cuerpo $id", mapOf("siniestro_id" to "SIN-1"),
        "2026-12-10T15:00:00Z", leida
    )

@RunWith(RobolectricTestRunner::class)
class NotificationsScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private val abiertas = mutableListOf<String>()
    private val eventos = mutableListOf<String>()

    private fun mostrar(
        bandeja: Bandeja? = null,
        cargando: Boolean = false,
        error: String? = null
    ) {
        compose.setContent {
            SolventaTheme {
                NotificationsScreen(
                    bandeja = bandeja,
                    cargando = cargando,
                    error = error,
                    onReintentar = { eventos += "reintentar" },
                    onVolver = { eventos += "volver" },
                    onAbrir = { abiertas += it.notificacionId }
                )
            }
        }
    }

    @Test
    fun muestraLaListaConLasNoLeidasMarcadas() {
        mostrar(Bandeja(listOf(notificacion("N-1", false), notificacion("N-2", true)), noLeidas = 1))

        compose.onNodeWithText("Título N-1").assertIsDisplayed()
        compose.onNodeWithText("Cuerpo N-2").assertIsDisplayed()
        compose.onNodeWithText("1 sin leer").assertIsDisplayed()
    }

    @Test
    fun conTodoLeidoDiceQueEstaAlDia() {
        mostrar(Bandeja(listOf(notificacion("N-1", true)), noLeidas = 0))

        compose.onNodeWithText("Estás al día").assertIsDisplayed()
    }

    @Test
    fun tocarUnaNotificacionLaAbre() {
        mostrar(Bandeja(listOf(notificacion("N-1", false)), noLeidas = 1))

        compose.onNodeWithText("Título N-1").performClick()

        assertEquals(listOf("N-1"), abiertas)
    }

    @Test
    fun sinNotificacionesMuestraElEstadoVacio() {
        mostrar(Bandeja(emptyList(), 0))

        compose.onNodeWithText("Aún no tienes notificaciones").assertIsDisplayed()
    }

    @Test
    fun mientrasCargaMuestraElIndicador() {
        mostrar(cargando = true)

        compose.onNodeWithContentDescription("Cargando tus notificaciones").assertIsDisplayed()
    }

    @Test
    fun unErrorSinDatosPermiteReintentar() {
        mostrar(error = "No pudimos cargar tus notificaciones.")

        compose.onNodeWithText("No pudimos cargar tus notificaciones.").assertIsDisplayed()
        compose.boton("Reintentar").performClick()

        assertEquals(listOf("reintentar"), eventos)
    }

    @Test
    fun unErrorConDatosNoEscondeLaLista() {
        mostrar(Bandeja(listOf(notificacion("N-1", false)), 1), error = "Sin conexión")

        compose.onNodeWithText("Sin conexión").assertIsDisplayed()
        compose.onNodeWithText("Título N-1").assertIsDisplayed()
    }
}

@RunWith(RobolectricTestRunner::class)
class ClaimDetailScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private fun siniestro(
        estado: EstadoSiniestro,
        origen: OrigenSiniestro = OrigenSiniestro.AUTOMATICO,
        monto: String? = null,
        motivo: String? = null
    ) = Siniestro(
        siniestroId = "SIN-1", polizaId = "SOL-PM-000001", origen = origen, estado = estado,
        eventoId = null, fechaEvento = "2026-10-20", horaEvento = "18:30:00",
        lugar = "Aeropuerto El Dorado", descripcion = "Retraso de vuelo", estimacionDanos = "500000.00",
        moneda = "COP", registradoEn = "2026-10-20T18:31:00Z",
        montoAprobado = monto, evaluadoEn = monto?.let { "2026-10-20T18:32:00Z" }, motivoRechazo = motivo
    )

    private fun mostrar(
        siniestro: Siniestro?,
        cargando: Boolean = false,
        error: String? = null
    ) {
        compose.setContent {
            SolventaTheme {
                ClaimDetailScreen(
                    siniestro = siniestro,
                    cargando = cargando,
                    error = error,
                    onReintentar = {},
                    onVolver = {}
                )
            }
        }
    }

    @Test
    fun unSiniestroAprobadoMuestraElMontoAprobado() {
        mostrar(siniestro(EstadoSiniestro.APROBADO, monto = "500000.00"))

        compose.onNodeWithText("Siniestro SIN-1").assertIsDisplayed()
        compose.onNodeWithText("Póliza SOL-PM-000001").assertIsDisplayed()
        compose.onNodeWithText("Siniestro paramétrico").assertIsDisplayed()
        compose.onNodeWithText("100%").assertIsDisplayed()
        compose.onNodeWithText("Pago aprobado").assertIsDisplayed()
        compose.onNodeWithText("Monto aprobado", substring = true).assertIsDisplayed()
    }

    @Test
    fun unSiniestroEnEvaluacionMuestraElAvanceDelCaso() {
        mostrar(siniestro(EstadoSiniestro.EN_EVALUACION, OrigenSiniestro.MANUAL))

        compose.onNodeWithText("60%").assertIsDisplayed()
        compose.onNodeWithText("Reporte recibido").assertIsDisplayed()
        compose.onNodeWithText("Evidencias validadas").assertIsDisplayed()
        compose.onNodeWithText("Evaluación en curso").assertIsDisplayed()
        compose.onNodeWithText("Recibirás una notificación").assertIsDisplayed()
    }

    @Test
    fun unSiniestroRegistradoApenasEmpieza() {
        mostrar(siniestro(EstadoSiniestro.REGISTRADO, OrigenSiniestro.MANUAL))

        compose.onNodeWithText("20%").assertIsDisplayed()
        compose.onNodeWithText("Pendiente de revisión").assertIsDisplayed()
    }

    @Test
    fun unSiniestroRechazadoMuestraElMotivo() {
        mostrar(
            siniestro(EstadoSiniestro.RECHAZADO, OrigenSiniestro.MANUAL, motivo = "Fuera de cobertura")
        )

        compose.onNodeWithText("Siniestro rechazado").assertIsDisplayed()
        compose.onNodeWithText("Fuera de cobertura", substring = true).assertIsDisplayed()
    }

    @Test
    fun cargandoSinDatosMuestraElIndicador() {
        mostrar(null, cargando = true)

        compose.onNodeWithContentDescription("Cargando el siniestro").assertIsDisplayed()
    }

    @Test
    fun siNoSeEncuentraSeAvisaYSePuedeReintentar() {
        mostrar(null)

        compose.onNodeWithText("No encontramos ese siniestro en tu cuenta.").assertIsDisplayed()
        compose.boton("Reintentar").assertIsDisplayed()
    }

    @Test
    fun unErrorAlRefrescarNoEscondeElDetalle() {
        mostrar(siniestro(EstadoSiniestro.EN_EVALUACION, OrigenSiniestro.MANUAL), error = "Sin conexión")

        compose.onNodeWithText("Sin conexión").assertIsDisplayed()
        compose.onNodeWithText("Evaluación en curso").assertIsDisplayed()
    }
}

@RunWith(RobolectricTestRunner::class)
class NotificacionesEnPerfilYHomeTest {
    @get:Rule
    val compose = createComposeRule()

    private val eventos = mutableListOf<String>()
    private val perfil = Perfil("u-1", "María", "Solano", "maria@correo.com", "CLIENTE")

    private fun mostrarPerfil(notificaciones: PreferenciasNotificacionesUi?) {
        compose.setContent {
            SolventaTheme {
                ProfileScreen(
                    perfil = perfil,
                    biometriaActivada = false,
                    sinConexion = false,
                    cerrandoSesion = false,
                    onCerrarSesion = {},
                    onInicio = {},
                    onPolizas = {},
                    onSiniestros = {},
                    notificaciones = notificaciones,
                    onCambiarPush = { eventos += "push:$it" },
                    onSolicitarPermisoNotificaciones = { eventos += "permiso" },
                    onAbrirAjustesNotificaciones = { eventos += "ajustes" }
                )
            }
        }
    }

    @Test
    fun sinNotificacionesDisponiblesLaOpcionSigueDeshabilitada() {
        mostrarPerfil(null)

        compose.onNodeWithText("Disponible próximamente").assertIsDisplayed()
    }

    @Test
    fun elInterruptorMuestraYCambiaLaPreferencia() {
        mostrarPerfil(PreferenciasNotificacionesUi(pushHabilitado = true))

        compose.onNodeWithText("Notificaciones push activadas").performClick()
        compose.onNodeWithContentDescription("Recibir notificaciones push").performClick()

        assertEquals(listOf("push:false"), eventos)
    }

    @Test
    fun alActivarSinPermisoSePideElPermiso() {
        mostrarPerfil(PreferenciasNotificacionesUi(pushHabilitado = false, permisoConcedido = false))

        compose.onNodeWithText("Push desactivado · los avisos se ven en la app").performClick()
        compose.onNodeWithContentDescription("Recibir notificaciones push").performClick()

        assertEquals(listOf("push:true", "permiso"), eventos)
    }

    @Test
    fun conElPushActivoYElPermisoBloqueadoSeOfreceDesbloquear() {
        mostrarPerfil(PreferenciasNotificacionesUi(pushHabilitado = true, permisoConcedido = false))

        compose.onNodeWithText("Notificaciones push activadas").performClick()
        compose.boton("Permitir").performClick()
        compose.boton("Abrir ajustes").performClick()

        assertEquals(listOf("permiso", "ajustes"), eventos)
    }

    @Test
    fun mientrasSeGuardaElInterruptorNoSeAcepta() {
        mostrarPerfil(PreferenciasNotificacionesUi(pushHabilitado = true, guardando = true))

        compose.onNodeWithText("Notificaciones push activadas").performClick()
        compose.onNodeWithContentDescription("Recibir notificaciones push").assertIsNotEnabled()
    }

    @Test
    fun unErrorAlGuardarSeMuestra() {
        mostrarPerfil(PreferenciasNotificacionesUi(pushHabilitado = true, error = "No pudimos guardar"))

        compose.onNodeWithText("Notificaciones push activadas").performClick()
        compose.onNodeWithText("No pudimos guardar").assertIsDisplayed()
        compose.onNodeWithContentDescription("Recibir notificaciones push").assertIsEnabled()
    }

    private fun mostrarInicio(sinLeer: Int, conAccion: Boolean = true) {
        compose.setContent {
            SolventaTheme {
                HomeScreen(
                    perfil = perfil,
                    biometriaActivada = false,
                    biometriaDisponible = false,
                    ofrecerActivarBiometria = false,
                    mensaje = null,
                    cerrandoSesion = false,
                    onActivarBiometria = {},
                    onSolicitarActivacion = {},
                    onDescartarActivacion = {},
                    onCerrarSesion = {},
                    notificacionesSinLeer = sinLeer,
                    onVerNotificaciones = if (conAccion) {
                        { eventos += "notificaciones" }
                    } else {
                        null
                    }
                )
            }
        }
    }

    @Test
    fun laCampanaMuestraCuantasHaySinLeerYAbreLaBandeja() {
        mostrarInicio(sinLeer = 3)

        compose.onNodeWithContentDescription("Notificaciones, 3 sin leer").performClick()

        assertEquals(listOf("notificaciones"), eventos)
    }

    @Test
    fun conMasDeNoventaYNueveSeAbrevia() {
        mostrarInicio(sinLeer = 120)

        compose.onNodeWithText("99+").assertIsDisplayed()
    }

    @Test
    fun sinNotificacionesPendientesLaCampanaNoLlevaNumero() {
        mostrarInicio(sinLeer = 0)

        compose.onNodeWithContentDescription("Notificaciones").assertIsDisplayed()
    }

    @Test
    fun sinBandejaDisponibleLaCampanaEstaDeshabilitada() {
        mostrarInicio(sinLeer = 0, conAccion = false)

        compose.onNodeWithContentDescription("Notificaciones").assertIsNotEnabled()
    }
}
