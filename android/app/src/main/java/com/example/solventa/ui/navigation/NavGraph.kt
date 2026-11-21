package com.example.solventa.ui.navigation

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.solventa.biometric.AutenticadorBiometrico
import com.example.solventa.biometric.DisponibilidadBiometrica
import com.example.solventa.biometric.FalloBiometrico
import com.example.solventa.biometric.mensaje
import com.example.solventa.domain.auth.MensajesAuth
import com.example.solventa.domain.asesor.DatosNuevoAsesor
import com.example.solventa.domain.asesor.DatosNuevoAnalista
import com.example.solventa.domain.cotizaciones.CatalogoCotizaciones
import com.example.solventa.domain.cotizaciones.EstadoCotizaciones
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.example.solventa.domain.notificaciones.DestinoNotificacion
import com.example.solventa.domain.notificaciones.EstadoNotificaciones
import com.example.solventa.domain.pagos.ConceptoPago
import com.example.solventa.domain.pagos.EstadoPago
import com.example.solventa.domain.pagos.EstadoPagos
import com.example.solventa.domain.siniestros.SolicitudSiniestro
import com.example.solventa.domain.siniestros.SolicitudSiniestroAsistido
import com.example.solventa.ui.auth.AuthViewModel
import com.example.solventa.ui.asesor.AsesorViewModel
import com.example.solventa.ui.billetera.BilleteraViewModel
import com.example.solventa.ui.billetera.abrirDocumento
import com.example.solventa.ui.billetera.compartirTexto
import com.example.solventa.ui.billetera.eliminarDocumentosTemporales
import com.example.solventa.ui.billetera.textoParaCompartir
import com.example.solventa.ui.cotizaciones.CotizacionesViewModel
import com.example.solventa.ui.components.SeccionNavegacion
import com.example.solventa.ui.components.SolventaBottomNavigation
import com.example.solventa.ui.notificaciones.AperturaNotificacion
import com.example.solventa.ui.notificaciones.NotificacionesViewModel
import com.example.solventa.ui.notificaciones.rememberSolicitudPermisoNotificaciones
import com.example.solventa.ui.pagos.PagosViewModel
import com.example.solventa.ui.siniestros.SiniestrosViewModel
import com.example.solventa.ui.asistencias.AsistenciasViewModel
import com.example.solventa.ui.siniestros.rememberCapturaEvidencias
import com.example.solventa.ui.screens.AdvisorHomeScreen
import com.example.solventa.ui.screens.AssistanceScreen
import com.example.solventa.ui.screens.PolizaAsistenciaElegible
import com.example.solventa.ui.screens.BiometricalLoginScreen
import com.example.solventa.ui.screens.CancelScreen
import com.example.solventa.ui.screens.CancelSuccessScreen
import com.example.solventa.ui.screens.CertificateScreen
import com.example.solventa.ui.screens.ClaimDetailScreen
import com.example.solventa.ui.screens.ClaimFormScreen
import com.example.solventa.ui.screens.ClaimsScreen
import com.example.solventa.ui.screens.CreateAdvisorScreen
import com.example.solventa.ui.screens.CreateAuditorScreen
import com.example.solventa.ui.screens.CredentialsLoginScreen
import com.example.solventa.ui.screens.HomeScreen
import com.example.solventa.ui.screens.NewQuoteScreen
import com.example.solventa.ui.screens.NotificationsScreen
import com.example.solventa.ui.screens.PaymentResultScreen
import com.example.solventa.ui.screens.PaymentScreen
import com.example.solventa.ui.screens.PaymentsScreen
import com.example.solventa.ui.screens.PolicyHistoryScreen
import com.example.solventa.ui.screens.PreferenciasNotificacionesUi
import com.example.solventa.ui.screens.ProfileScreen
import com.example.solventa.ui.screens.PsePortalScreen
import com.example.solventa.ui.screens.QuoteFormScreen
import com.example.solventa.ui.screens.QuoteResultScreen
import com.example.solventa.ui.screens.QuotesScreen
import com.example.solventa.ui.screens.RegisterScreen
import com.example.solventa.ui.screens.RenewalScreen
import com.example.solventa.ui.screens.RenewalSuccessScreen
import com.example.solventa.ui.screens.WalletScreen
import com.example.solventa.ui.screens.WelcomeScreen
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first

@Composable
fun NavGraph(
    viewModel: AuthViewModel,
    autenticador: AutenticadorBiometrico,
    modifier: Modifier = Modifier,
    navController: NavHostController = rememberNavController(),
    startDestination: String = ScreenRoute.Welcome.route,
    billetera: BilleteraViewModel? = null,
    cotizaciones: CotizacionesViewModel? = null,
    pagos: PagosViewModel? = null,
    siniestros: SiniestrosViewModel? = null,
    asesor: AsesorViewModel? = null,
    notificaciones: NotificacionesViewModel? = null,
    aperturaPendiente: AperturaNotificacion? = null,
    onAperturaConsumida: () -> Unit = {},
    asistencias: AsistenciasViewModel? = null
) {
    val estado by viewModel.estado.collectAsState()
    val estadoCotizaciones = cotizaciones?.estado?.collectAsState()?.value ?: EstadoCotizaciones()
    val estadoPagos = pagos?.estado?.collectAsState()?.value ?: EstadoPagos()
    val estadoNotificaciones = notificaciones?.estado?.collectAsState()?.value ?: EstadoNotificaciones()
    val autenticado = estado.sesion != null
    // Las notificaciones son del cliente: asesores y servicio interno no tienen bandeja.
    val esCliente = estado.sesion?.perfil?.rol == "CLIENTE"
    val notificacionesDelCliente = notificaciones.takeIf { esCliente }
    val usuarioId = estado.sesion?.perfil?.id
    val contextoAplicacion = LocalContext.current.applicationContext
    var ultimoUsuarioAutenticado by remember { mutableStateOf<String?>(null) }

    // Guardia de navegación: con sesión se va al inicio; sin sesión nadie se queda en una
    // pantalla privada (inicio, billetera o certificado) y se descarta lo que se cargó.
    LaunchedEffect(usuarioId) {
        val usuarioAnterior = ultimoUsuarioAutenticado
        when {
            usuarioId == null && usuarioAnterior != null -> {
                billetera?.eliminarDatosLocales()
                contextoAplicacion.eliminarDocumentosTemporales()
            }
            usuarioId == null -> billetera?.limpiar()
            else -> {
                if (usuarioAnterior != null && usuarioAnterior != usuarioId) {
                    contextoAplicacion.eliminarDocumentosTemporales()
                }
                billetera?.registrarUsuario(usuarioId)
            }
        }
        ultimoUsuarioAutenticado = usuarioId

        val actual = navController.currentDestination?.route
        if (!autenticado) {
            cotizaciones?.limpiar()
            pagos?.limpiar()
            siniestros?.limpiar()
            asesor?.limpiar()
            notificaciones?.limpiar()
            asistencias?.limpiar()
        }
        if (autenticado && actual !in ScreenRoute.privadas) {
            navController.navigate(ScreenRoute.Home.route) {
                popUpTo(navController.graph.id) { inclusive = true }
                launchSingleTop = true
            }
        } else if (!autenticado && actual in ScreenRoute.privadas) {
            navController.navigate(ScreenRoute.BiometricalLogin.route) {
                popUpTo(navController.graph.id) { inclusive = true }
                launchSingleTop = true
            }
        }
    }

    LaunchedEffect(estado.registroCompletado) {
        if (estado.registroCompletado) {
            viewModel.consumirRegistroCompletado()
            navController.navigate(ScreenRoute.CredentialsLogin.route) {
                popUpTo(ScreenRoute.Register.route) { inclusive = true }
                launchSingleTop = true
            }
        }
    }

    // Al iniciar sesión el cliente registra el token de push de este teléfono y consulta su insignia.
    LaunchedEffect(usuarioId, esCliente) {
        if (esCliente) {
            notificaciones?.registrarDispositivo()
            notificaciones?.actualizarInsignia()
        }
    }

    // A dónde lleva cada destino de notificación; null si esa parte de la app no está disponible.
    val rutaDelDestino: (DestinoNotificacion) -> String? = { destino ->
        when (destino) {
            is DestinoNotificacion.Renovacion ->
                if (billetera != null) ScreenRoute.Renewal.ruta(destino.polizaId) else null
            is DestinoNotificacion.DetalleSiniestro ->
                if (siniestros != null) ScreenRoute.ClaimDetail.ruta(destino.siniestroId) else null
            DestinoNotificacion.Bandeja ->
                if (notificaciones != null) ScreenRoute.Notifications.route else null
        }
    }

    // Se tocó una notificación del sistema: con sesión se abre su destino; sin sesión espera al
    // ingreso. Se espera a estar en una pantalla privada para no pisar la guardia de arriba.
    LaunchedEffect(aperturaPendiente, esCliente) {
        val apertura = aperturaPendiente ?: return@LaunchedEffect
        if (!esCliente) return@LaunchedEffect
        navController.currentBackStackEntryFlow.first { it.destination.route in ScreenRoute.privadas }
        val ruta = rutaDelDestino(apertura.destino)
        if (ruta != null) {
            navController.navigate(ruta) { launchSingleTop = true }
        }
        apertura.notificacionId?.let { notificaciones?.marcarLeida(it) }
        onAperturaConsumida()
    }

    // Da de baja el teléfono antes de cerrar la sesión, que es lo que autoriza la baja.
    val cerrarSesionCliente: () -> Unit = {
        val cerrar = {
            billetera?.eliminarDatosLocales()
            viewModel.cerrarSesion()
        }
        if (notificacionesDelCliente != null) notificacionesDelCliente.cerrarSesionConBaja(cerrar) else cerrar()
    }

    NavHost(
        navController = navController,
        startDestination = startDestination,
        modifier = modifier
    ) {
        composable(route = ScreenRoute.Welcome.route) {
            WelcomeScreen(
                onLoginClick = {
                    navController.navigate(ScreenRoute.BiometricalLogin.route)
                },
                onRegisterClick = {
                    viewModel.consumirMensaje()
                    navController.navigate(ScreenRoute.Register.route)
                }
            )
        }

        composable(route = ScreenRoute.BiometricalLogin.route) {
            val disponibilidad = remember { autenticador.disponibilidad() }
            val disponible = disponibilidad == DisponibilidadBiometrica.DISPONIBLE

            LaunchedEffect(estado.requiereCredenciales) {
                if (estado.requiereCredenciales) {
                    viewModel.credencialesMostradas()
                    navController.navigate(ScreenRoute.CredentialsLogin.route) {
                        launchSingleTop = true
                    }
                }
            }

            BiometricalLoginScreen(
                biometriaDisponible = disponible,
                cargando = estado.cargando,
                mensaje = estado.mensaje ?: disponibilidad.mensaje(),
                onBiometricClick = {
                    if (viewModel.solicitarIngresoBiometrico()) {
                        autenticador.autenticar(
                            titulo = "Ingresa a Solventa",
                            subtitulo = "Usa la huella o el rostro configurados en tu dispositivo",
                            alExito = viewModel::ingresarConBiometria,
                            alFallo = viewModel::falloBiometrico,
                            alNoCoincidir = viewModel::huellaNoReconocida
                        )
                    }
                },
                onUseCredentialsClick = {
                    viewModel.consumirMensaje()
                    navController.navigate(ScreenRoute.CredentialsLogin.route)
                },
                onBackClick = {
                    viewModel.consumirMensaje()
                    if (!navController.popBackStack()) {
                        navController.navigate(ScreenRoute.Welcome.route)
                    }
                },
                onRegisterClick = {
                    viewModel.consumirMensaje()
                    navController.navigate(ScreenRoute.Register.route)
                }
            )
        }

        composable(route = ScreenRoute.CredentialsLogin.route) {
            CredentialsLoginScreen(
                cargando = estado.cargando,
                mensaje = estado.mensaje,
                onLoginSubmit = viewModel::ingresarConCredenciales,
                onSwitchToBiometric = {
                    viewModel.consumirMensaje()
                    if (!navController.popBackStack(ScreenRoute.BiometricalLogin.route, inclusive = false)) {
                        navController.navigate(ScreenRoute.BiometricalLogin.route)
                    }
                },
                onBackClick = {
                    viewModel.consumirMensaje()
                    navController.popBackStack()
                }
            )
        }

        composable(route = ScreenRoute.Register.route) {
            RegisterScreen(
                onBackClick = {
                    navController.popBackStack()
                },
                onRegisterSubmit = viewModel::registrar,
                cargando = estado.cargando,
                mensaje = estado.mensaje,
                onLoginClick = {
                    viewModel.consumirMensaje()
                    navController.navigate(ScreenRoute.BiometricalLogin.route)
                }
            )
        }

        composable(route = ScreenRoute.Home.route) {
            val sesion = estado.sesion
            if (sesion == null) {
                // Sin sesión no se compone nada con datos; la guardia redirige al ingreso.
                Box(modifier = Modifier.fillMaxSize())
            } else if (sesion.perfil.rol == "ASESOR_VENTAS" && asesor != null) {
                val estadoAsesor by asesor.estado.collectAsState()
                LaunchedEffect(Unit) { asesor.cargarClientes() }
                LaunchedEffect(sesion.expiraEnMs) {
                    delay((sesion.expiraEnMs - System.currentTimeMillis()).coerceAtLeast(0))
                    viewModel.verificarExpiracion()
                }
                val aviso = estadoAsesor.clienteAsociado?.let {
                    "Cliente ${it.nombre} ${it.apellido} asociado."
                }
                AdvisorHomeScreen(
                    nombre = sesion.perfil.nombre,
                    clientes = estadoAsesor.clientes,
                    cargando = estadoAsesor.cargando,
                    error = estadoAsesor.error,
                    asociando = estadoAsesor.asociando,
                    errorAsociar = estadoAsesor.errorAsociar,
                    avisoAsociado = aviso,
                    cerrandoSesion = estado.cargando,
                    onAsociarCliente = { email ->
                        asesor.consumirErrorAsociar()
                        asesor.asociarCliente(email)
                    },
                    onRegistrarSiniestro = { cliente ->
                        asesor.seleccionarCliente(cliente)
                        navController.navigate(ScreenRoute.AssistedClaimForm.ruta(cliente.clienteId)) {
                            launchSingleTop = true
                        }
                    },
                    onCerrarSesion = viewModel::cerrarSesion
                )
            } else {
                val estadoBilletera = billetera?.estado?.collectAsState()?.value
                LaunchedEffect(billetera) { billetera?.cargar() }

                // Expiración: al vencer el access token se cierra la sesión en memoria.
                LaunchedEffect(sesion.expiraEnMs) {
                    delay((sesion.expiraEnMs - System.currentTimeMillis()).coerceAtLeast(0))
                    viewModel.verificarExpiracion()
                }

                val biometriaDisponible = remember { autenticador.disponibilidad() } ==
                    DisponibilidadBiometrica.DISPONIBLE
                // La insignia de la campana se refresca cada vez que se vuelve al inicio.
                LaunchedEffect(notificacionesDelCliente) { notificacionesDelCliente?.actualizarInsignia() }

                HomeScreen(
                    perfil = sesion.perfil,
                    notificacionesSinLeer = estadoNotificaciones.noLeidas,
                    onVerNotificaciones = notificacionesDelCliente?.let {
                        {
                            navController.navigate(ScreenRoute.Notifications.route) {
                                launchSingleTop = true
                            }
                        }
                    },
                    biometriaActivada = estado.biometriaActivada,
                    biometriaDisponible = biometriaDisponible,
                    ofrecerActivarBiometria = estado.ofrecerActivarBiometria && biometriaDisponible,
                    mensaje = estado.mensaje,
                    cerrandoSesion = estado.cargando,
                    onActivarBiometria = {
                        viewModel.prepararActivacion()
                        autenticador.autenticar(
                            titulo = "Activa el ingreso con huella",
                            subtitulo = "Confirma con la huella o el rostro de tu dispositivo",
                            alExito = viewModel::activarBiometria,
                            alFallo = { fallo ->
                                val cancelado = fallo is FalloBiometrico.Cancelado ||
                                    fallo is FalloBiometrico.UsarCredenciales
                                viewModel.descartarActivacion(
                                    if (cancelado) null else MensajesAuth.ACTIVACION_FALLIDA
                                )
                            },
                            alNoCoincidir = {}
                        )
                    },
                    onSolicitarActivacion = viewModel::solicitarActivacion,
                    onDescartarActivacion = { viewModel.descartarActivacion() },
                    // Inicia el borrado inmediatamente; la guardia también lo confirma cuando
                    // observe que la sesión quedó cerrada.
                    onCerrarSesion = cerrarSesionCliente,
                    onCotizarSeguro = {
                        navController.navigate(ScreenRoute.NewQuote.route) { launchSingleTop = true }
                    },
                    onVerCotizaciones = cotizaciones?.let {
                        { navController.navigate(ScreenRoute.Quotes.route) { launchSingleTop = true } }
                    },
                    onVerBilletera = billetera?.let {
                        { navController.navigate(ScreenRoute.Wallet.ruta()) { launchSingleTop = true } }
                    },
                    onVerPagos = pagos?.let {
                        { navController.navigate(ScreenRoute.Payments.route) { launchSingleTop = true } }
                    },
                    onVerSiniestros = siniestros?.let {
                        { navController.navigate(ScreenRoute.Claims.ruta()) { launchSingleTop = true } }
                    },
                    onVerAsistencia = asistencias?.let {
                        {
                            asistencias.reiniciarFlujo()
                            navController.navigate(ScreenRoute.Assistance.route) {
                                launchSingleTop = true
                            }
                        }
                    },
                    onNavbarPolizas = billetera?.let {
                        {
                            navController.navigate(ScreenRoute.Wallet.ruta(desdeNavbar = true)) {
                                launchSingleTop = true
                            }
                        }
                    },
                    onNavbarSiniestros = siniestros?.let {
                        {
                            navController.navigate(ScreenRoute.Claims.ruta(desdeNavbar = true)) {
                                launchSingleTop = true
                            }
                        }
                    },
                    onNavbarPerfil = {
                        navController.navigate(ScreenRoute.Profile.route) {
                            launchSingleTop = true
                        }
                    },
                    cantidadPolizasActivas = estadoBilletera?.billetera?.totalVigentes,
                    sinConexion = estadoBilletera?.sinConexion == true,
                    ultimaSincronizacionMs = estadoBilletera?.ultimaSincronizacionMs,
                    onCrearAsesor = if (sesion.perfil.rol == "SERVICIO_INTERNO" && asesor != null) {
                        { navController.navigate(ScreenRoute.CreateAdvisor.route) { launchSingleTop = true } }
                    } else {
                        null
                    },
                    onCrearAnalista = if (sesion.perfil.rol == "SERVICIO_INTERNO" && asesor != null) {
                        { navController.navigate(ScreenRoute.CreateAuditor.route) { launchSingleTop = true } }
                    } else {
                        null
                    }
                )
            }
        }

        if (notificaciones != null) {
            composable(route = ScreenRoute.Notifications.route) {
                if (estado.sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    // Se vuelve a pedir cada vez que se entra: el backend es la fuente de verdad.
                    LaunchedEffect(Unit) { notificaciones.cargar() }
                    NotificationsScreen(
                        bandeja = estadoNotificaciones.bandeja,
                        cargando = estadoNotificaciones.cargando,
                        error = estadoNotificaciones.error,
                        onReintentar = { notificaciones.cargar() },
                        onVolver = { navController.popBackStack() },
                        onAbrir = { notificacion ->
                            notificaciones.marcarLeida(notificacion.notificacionId)
                            rutaDelDestino(notificacion.destino)
                                ?.takeIf { it != ScreenRoute.Notifications.route }
                                ?.let { ruta ->
                                    navController.navigate(ruta) { launchSingleTop = true }
                                }
                        }
                    )
                }
            }
        }

        composable(route = ScreenRoute.Profile.route) {
            val sesion = estado.sesion
            if (sesion == null) {
                Box(modifier = Modifier.fillMaxSize())
            } else {
                val estadoBilletera = billetera?.estado?.collectAsState()?.value
                val permisoNotificaciones = rememberSolicitudPermisoNotificaciones()
                LaunchedEffect(notificacionesDelCliente) { notificacionesDelCliente?.cargarPreferencia() }
                ProfileScreen(
                    perfil = sesion.perfil,
                    notificaciones = notificacionesDelCliente?.let {
                        PreferenciasNotificacionesUi(
                            pushHabilitado = estadoNotificaciones.pushHabilitado,
                            guardando = estadoNotificaciones.cambiandoPreferencia,
                            error = estadoNotificaciones.errorPreferencia,
                            permisoConcedido = permisoNotificaciones.concedido
                        )
                    },
                    onCambiarPush = { notificacionesDelCliente?.cambiarPreferencia(it) },
                    onSolicitarPermisoNotificaciones = permisoNotificaciones.solicitar,
                    onAbrirAjustesNotificaciones = permisoNotificaciones.abrirAjustes,
                    biometriaActivada = estado.biometriaActivada,
                    sinConexion = estadoBilletera?.sinConexion == true,
                    cerrandoSesion = estado.cargando,
                    onCerrarSesion = cerrarSesionCliente,
                    onInicio = {
                        navController.popBackStack(ScreenRoute.Home.route, false)
                    },
                    onPolizas = billetera?.let {
                        {
                            navController.navigate(ScreenRoute.Wallet.ruta(desdeNavbar = true)) {
                                popUpTo(ScreenRoute.Home.route)
                                launchSingleTop = true
                            }
                        }
                    },
                    onSiniestros = siniestros?.let {
                        {
                            navController.navigate(ScreenRoute.Claims.ruta(desdeNavbar = true)) {
                                popUpTo(ScreenRoute.Home.route)
                                launchSingleTop = true
                            }
                        }
                    }
                )
            }
        }

        composable(route = ScreenRoute.NewQuote.route) {
            if (estado.sesion == null) {
                Box(modifier = Modifier.fillMaxSize())
            } else {
                NewQuoteScreen(
                    onVolver = { navController.popBackStack() },
                    onSeleccionarRamo = { ramo ->
                        navController.navigate(ScreenRoute.QuoteForm.ruta(ramo)) {
                            launchSingleTop = true
                        }
                    },
                    onInicio = { navController.popBackStack(ScreenRoute.Home.route, false) },
                    onVerBilletera = billetera?.let {
                        { navController.navigate(ScreenRoute.Wallet.ruta()) { launchSingleTop = true } }
                    }
                )
            }
        }

        composable(
            route = ScreenRoute.QuoteForm.route,
            arguments = listOf(
                navArgument(ScreenRoute.QuoteForm.ARGUMENTO) { type = NavType.StringType }
            )
        ) { entrada ->
            val ramo = entrada.arguments?.getString(ScreenRoute.QuoteForm.ARGUMENTO)
                ?.let(RamoCotizacion::desdeCodigoApi)
            val sesion = estado.sesion
            if (sesion == null || ramo == null) {
                Box(modifier = Modifier.fillMaxSize())
            } else {
                LaunchedEffect(estadoCotizaciones.resultado?.cotizacionId) {
                    val resultado = estadoCotizaciones.resultado
                    if (resultado?.ramo == ramo) {
                        navController.navigate(ScreenRoute.QuoteResult.ruta(ramo)) {
                            launchSingleTop = true
                        }
                    }
                }
                QuoteFormScreen(
                    definicion = CatalogoCotizaciones.definicion(ramo),
                    onVolver = { navController.popBackStack() },
                    onCalcular = { valores ->
                        cotizaciones?.cotizar(sesion.perfil.id, ramo, valores)
                    },
                    cargando = estadoCotizaciones.cargando,
                    errorRemoto = estadoCotizaciones.error,
                    onInicio = { navController.popBackStack(ScreenRoute.Home.route, false) },
                    onVerBilletera = billetera?.let {
                        { navController.navigate(ScreenRoute.Wallet.ruta()) { launchSingleTop = true } }
                    }
                )
            }
        }

        composable(
            route = ScreenRoute.QuoteResult.route,
            arguments = listOf(
                navArgument(ScreenRoute.QuoteResult.ARGUMENTO) { type = NavType.StringType }
            )
        ) { entrada ->
            val ramo = entrada.arguments?.getString(ScreenRoute.QuoteResult.ARGUMENTO)
                ?.let(RamoCotizacion::desdeCodigoApi)
            val resultado = estadoCotizaciones.resultado?.takeIf { it.ramo == ramo }
            if (estado.sesion == null || ramo == null || resultado == null) {
                Box(modifier = Modifier.fillMaxSize())
            } else {
                QuoteResultScreen(
                    cotizacion = resultado,
                    onVolver = {
                        cotizaciones?.limpiarResultado()
                        navController.popBackStack()
                    },
                    onAceptar = {
                        if (pagos != null) {
                            pagos.limpiar()
                            navController.navigate(ScreenRoute.Payment.ruta(resultado.cotizacionId)) {
                                launchSingleTop = true
                            }
                        }
                    },
                    onCrearOtra = {
                        cotizaciones?.limpiarResultado()
                        navController.popBackStack(ScreenRoute.NewQuote.route, inclusive = false)
                    },
                    onInicio = {
                        cotizaciones?.limpiarResultado()
                        navController.popBackStack(ScreenRoute.Home.route, false)
                    },
                    onVerBilletera = billetera?.let {
                        { navController.navigate(ScreenRoute.Wallet.ruta()) { launchSingleTop = true } }
                    }
                )
            }
        }

        if (cotizaciones != null) {
            composable(route = ScreenRoute.Quotes.route) {
                val sesion = estado.sesion
                if (sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    LaunchedEffect(sesion.perfil.id) { cotizaciones.listar(sesion.perfil.id) }
                    QuotesScreen(
                        cotizaciones = estadoCotizaciones.listado,
                        cargando = estadoCotizaciones.cargandoListado,
                        error = estadoCotizaciones.errorListado,
                        onVerCotizacion = { cotizacionId ->
                            navController.navigate(ScreenRoute.QuoteHistoryDetail.ruta(cotizacionId))
                        },
                        onReintentar = { cotizaciones.listar(sesion.perfil.id) },
                        onVolver = { navController.popBackStack() },
                        onCrearCotizacion = {
                            navController.navigate(ScreenRoute.NewQuote.route) { launchSingleTop = true }
                        }
                    )
                }
            }

            composable(
                route = ScreenRoute.QuoteHistoryDetail.route,
                arguments = listOf(
                    navArgument(ScreenRoute.QuoteHistoryDetail.ARGUMENTO) {
                        type = NavType.StringType
                    }
                )
            ) { entrada ->
                val cotizacionId = entrada.arguments
                    ?.getString(ScreenRoute.QuoteHistoryDetail.ARGUMENTO)
                val cotizacion = estadoCotizaciones.listado
                    .firstOrNull { it.cotizacionId == cotizacionId }
                if (estado.sesion == null || cotizacion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    QuoteResultScreen(
                        cotizacion = cotizacion,
                        onVolver = { navController.popBackStack() },
                        onAceptar = {
                            if (pagos != null) {
                                pagos.limpiar()
                                navController.navigate(
                                    ScreenRoute.Payment.ruta(cotizacion.cotizacionId)
                                ) { launchSingleTop = true }
                            }
                        },
                        onCrearOtra = {
                            cotizaciones.limpiarResultado()
                            navController.navigate(ScreenRoute.NewQuote.route) {
                                launchSingleTop = true
                            }
                        },
                        onInicio = {
                            navController.popBackStack(ScreenRoute.Home.route, false)
                        },
                        onVerBilletera = billetera?.let {
                            {
                                navController.navigate(ScreenRoute.Wallet.ruta()) {
                                    launchSingleTop = true
                                }
                            }
                        },
                        modoDetalle = true
                    )
                }
            }
        }

        if (billetera != null) {
            composable(
                route = ScreenRoute.Wallet.route,
                arguments = listOf(
                    navArgument(ScreenRoute.Wallet.ORIGEN_NAVBAR) {
                        type = NavType.BoolType
                        defaultValue = false
                    }
                )
            ) { entrada ->
                val desdeNavbar = entrada.arguments?.getBoolean(ScreenRoute.Wallet.ORIGEN_NAVBAR) == true
                val estadoBilletera by billetera.estado.collectAsState()
                if (estado.sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    // Se vuelve a pedir cada vez que se entra: el backend es la fuente de verdad.
                    LaunchedEffect(Unit) { billetera.cargar() }
                    PantallaConNavegacion(
                        visible = desdeNavbar,
                        seleccionada = SeccionNavegacion.POLIZAS,
                        navController = navController,
                        polizasDisponibles = true,
                        siniestrosDisponibles = siniestros != null
                    ) { pantallaModifier ->
                        WalletScreen(
                            billetera = estadoBilletera.billetera,
                            cargando = estadoBilletera.cargando,
                            error = estadoBilletera.error,
                            sinConexion = estadoBilletera.sinConexion,
                            ultimaSincronizacionMs = estadoBilletera.ultimaSincronizacionMs,
                            datosAntiguos = estadoBilletera.datosAntiguos,
                            falloSincronizacionPersistente =
                                estadoBilletera.falloSincronizacionPersistente,
                            onVerPoliza = { polizaId ->
                                navController.navigate(
                                    ScreenRoute.Certificate.ruta(polizaId, desdeNavbar)
                                )
                            },
                            onReintentar = billetera::cargar,
                            onVolver = { navController.popBackStack() },
                            modifier = pantallaModifier
                        )
                    }
                }
            }

            composable(
                route = ScreenRoute.Certificate.route,
                arguments = listOf(
                    navArgument(ScreenRoute.Certificate.ARGUMENTO) { type = NavType.StringType },
                    navArgument(ScreenRoute.Certificate.ORIGEN_NAVBAR) {
                        type = NavType.BoolType
                        defaultValue = false
                    }
                )
            ) { entrada ->
                val polizaId = entrada.arguments?.getString(ScreenRoute.Certificate.ARGUMENTO).orEmpty()
                val desdeNavbar =
                    entrada.arguments?.getBoolean(ScreenRoute.Certificate.ORIGEN_NAVBAR) == true
                val estadoBilletera by billetera.estado.collectAsState()
                val contexto = LocalContext.current

                if (estado.sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    LaunchedEffect(polizaId) {
                        billetera.verCertificado(polizaId)
                    }
                    DisposableEffect(polizaId) { onDispose { billetera.cerrarCertificado() } }

                    LaunchedEffect(estadoBilletera.enlaceParaCompartir) {
                        val enlace = estadoBilletera.enlaceParaCompartir ?: return@LaunchedEffect
                        billetera.enlaceCompartido()
                        contexto.compartirTexto(
                            textoParaCompartir(estadoBilletera.certificado?.numeroPoliza, enlace)
                        )
                    }

                    LaunchedEffect(estadoBilletera.documentoParaAbrir) {
                        val documento = estadoBilletera.documentoParaAbrir
                            ?: return@LaunchedEffect
                        billetera.documentoAbierto(contexto.abrirDocumento(documento))
                    }

                    val certificado = estadoBilletera.certificado?.takeIf { it.polizaId == polizaId }
                    PantallaConNavegacion(
                        visible = desdeNavbar,
                        seleccionada = SeccionNavegacion.POLIZAS,
                        navController = navController,
                        polizasDisponibles = true,
                        siniestrosDisponibles = siniestros != null
                    ) { pantallaModifier ->
                        CertificateScreen(
                            certificado = certificado,
                            cargando = estadoBilletera.cargandoCertificado,
                            error = estadoBilletera.errorCertificado,
                            descargandoDocumento = estadoBilletera.descargandoDocumento,
                            compartiendo = estadoBilletera.compartiendo,
                            mensaje = estadoBilletera.mensaje,
                            onVerDocumento = { billetera.descargarDocumento(polizaId) },
                            onCompartir = { billetera.compartir(polizaId) },
                            onVerHistorial = {
                                navController.navigate(
                                    ScreenRoute.PolicyHistory.ruta(polizaId, desdeNavbar)
                                )
                            },
                            onReintentar = {
                                billetera.verCertificado(polizaId)
                            },
                            onVolver = { navController.popBackStack() },
                            modifier = pantallaModifier,
                            onRenovar = {
                                navController.navigate(ScreenRoute.Renewal.ruta(polizaId, desdeNavbar))
                            },
                            onCancelar = {
                                navController.navigate(ScreenRoute.Cancel.ruta(polizaId, desdeNavbar))
                            }
                        )
                    }
                }
            }

            composable(
                route = ScreenRoute.Renewal.route,
                arguments = listOf(
                    navArgument(ScreenRoute.Renewal.ARGUMENTO) { type = NavType.StringType },
                    navArgument(ScreenRoute.Renewal.ORIGEN_NAVBAR) {
                        type = NavType.BoolType
                        defaultValue = false
                    }
                )
            ) { entrada ->
                val polizaId = entrada.arguments?.getString(ScreenRoute.Renewal.ARGUMENTO).orEmpty()
                val desdeNavbar =
                    entrada.arguments?.getBoolean(ScreenRoute.Renewal.ORIGEN_NAVBAR) == true
                val estadoBilletera by billetera.estado.collectAsState()

                if (estado.sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    LaunchedEffect(polizaId) { billetera.verPropuestaRenovacion(polizaId) }
                    DisposableEffect(polizaId) { onDispose { billetera.cerrarRenovacion() } }

                    // Con la renovación creada se paga su cotización con el recaudo de siempre.
                    LaunchedEffect(estadoBilletera.renovacionParaPagar) {
                        val renovacion = estadoBilletera.renovacionParaPagar ?: return@LaunchedEffect
                        billetera.renovacionEnPago()
                        // Sin recaudo disponible no hay ruta de pago a la que ir.
                        if (pagos != null) {
                            pagos.limpiar()
                            navController.navigate(ScreenRoute.Payment.ruta(renovacion.cotizacionId))
                        }
                    }

                    PantallaConNavegacion(
                        visible = desdeNavbar,
                        seleccionada = SeccionNavegacion.POLIZAS,
                        navController = navController,
                        polizasDisponibles = true,
                        siniestrosDisponibles = siniestros != null
                    ) { pantallaModifier ->
                        RenewalScreen(
                            propuesta = estadoBilletera.propuestaRenovacion
                                ?.takeIf { it.polizaId == polizaId },
                            cargando = estadoBilletera.cargandoRenovacion,
                            error = estadoBilletera.errorRenovacion,
                            iniciando = estadoBilletera.iniciandoRenovacion,
                            onConfirmar = { billetera.iniciarRenovacion(polizaId) },
                            onReintentar = { billetera.verPropuestaRenovacion(polizaId) },
                            onAhoraNo = { navController.popBackStack() },
                            onVolver = { navController.popBackStack() },
                            modifier = pantallaModifier
                        )
                    }
                }
            }

            composable(
                route = ScreenRoute.PolicyHistory.route,
                arguments = listOf(
                    navArgument(ScreenRoute.PolicyHistory.ARGUMENTO) { type = NavType.StringType },
                    navArgument(ScreenRoute.PolicyHistory.ORIGEN_NAVBAR) {
                        type = NavType.BoolType
                        defaultValue = false
                    }
                )
            ) { entrada ->
                val polizaId =
                    entrada.arguments?.getString(ScreenRoute.PolicyHistory.ARGUMENTO).orEmpty()
                val desdeNavbar =
                    entrada.arguments?.getBoolean(ScreenRoute.PolicyHistory.ORIGEN_NAVBAR) == true
                val estadoBilletera by billetera.estado.collectAsState()

                if (estado.sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    LaunchedEffect(polizaId) { billetera.verHistorialPoliza(polizaId) }
                    DisposableEffect(polizaId) { onDispose { billetera.cerrarHistorial() } }

                    val certificado =
                        estadoBilletera.certificado?.takeIf { it.polizaId == polizaId }
                    val resumen = estadoBilletera.billetera?.polizas
                        ?.firstOrNull { it.polizaId == polizaId }
                    val historialPoliza =
                        estadoBilletera.historial?.takeIf { it.polizaId == polizaId }
                    val numeroPoliza = historialPoliza?.numeroPoliza?.takeIf { it.isNotBlank() }
                        ?: certificado?.numeroPoliza
                        ?: resumen?.numeroPoliza.orEmpty()
                    val nombreRamo = historialPoliza?.nombreRamo?.takeIf { it.isNotBlank() }
                        ?: certificado?.nombreRamo
                        ?: resumen?.nombreRamo.orEmpty()

                    PantallaConNavegacion(
                        visible = desdeNavbar,
                        seleccionada = SeccionNavegacion.POLIZAS,
                        navController = navController,
                        polizasDisponibles = true,
                        siniestrosDisponibles = siniestros != null
                    ) { pantallaModifier ->
                        PolicyHistoryScreen(
                            numeroPoliza = numeroPoliza,
                            nombreRamo = nombreRamo,
                            historial = historialPoliza,
                            cargando = estadoBilletera.cargandoHistorial,
                            error = estadoBilletera.errorHistorial,
                            onReintentar = { billetera.verHistorialPoliza(polizaId) },
                            onVolver = { navController.popBackStack() },
                            modifier = pantallaModifier
                        )
                    }
                }
            }
        }

        if (billetera != null) {
            composable(
                route = ScreenRoute.Cancel.route,
                arguments = listOf(
                    navArgument(ScreenRoute.Cancel.ARGUMENTO) { type = NavType.StringType },
                    navArgument(ScreenRoute.Cancel.ORIGEN_NAVBAR) {
                        type = NavType.BoolType
                        defaultValue = false
                    }
                )
            ) { entrada ->
                val polizaId = entrada.arguments?.getString(ScreenRoute.Cancel.ARGUMENTO).orEmpty()
                val desdeNavbar =
                    entrada.arguments?.getBoolean(ScreenRoute.Cancel.ORIGEN_NAVBAR) == true
                val estadoBilletera by billetera.estado.collectAsState()

                if (estado.sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    LaunchedEffect(polizaId) { billetera.verPropuestaCancelacion(polizaId) }
                    DisposableEffect(polizaId) { onDispose { billetera.cerrarCancelacion() } }

                    val volverALasPolizas = {
                        if (!navController.popBackStack(ScreenRoute.Wallet.route, false)) {
                            navController.popBackStack(ScreenRoute.Home.route, false)
                        }
                        Unit
                    }

                    PantallaConNavegacion(
                        visible = desdeNavbar,
                        seleccionada = SeccionNavegacion.POLIZAS,
                        navController = navController,
                        polizasDisponibles = true,
                        siniestrosDisponibles = siniestros != null
                    ) { pantallaModifier ->
                        if (estadoBilletera.cancelacionRealizada?.polizaId == polizaId) {
                            CancelSuccessScreen(
                                onVolverALasPolizas = volverALasPolizas,
                                onVolver = volverALasPolizas,
                                modifier = pantallaModifier
                            )
                        } else {
                            CancelScreen(
                                propuesta = estadoBilletera.propuestaCancelacion
                                    ?.takeIf { it.polizaId == polizaId },
                                cargando = estadoBilletera.cargandoCancelacion,
                                error = estadoBilletera.errorCancelacion,
                                cancelando = estadoBilletera.cancelando,
                                onConfirmar = { motivo -> billetera.cancelarPoliza(polizaId, motivo) },
                                onReintentar = { billetera.verPropuestaCancelacion(polizaId) },
                                onConservar = { navController.popBackStack() },
                                onVolver = { navController.popBackStack() },
                                modifier = pantallaModifier
                            )
                        }
                    }
                }
            }
        }

        if (pagos != null) {
            composable(
                route = ScreenRoute.Payment.route,
                arguments = listOf(
                    navArgument(ScreenRoute.Payment.ARGUMENTO) { type = NavType.StringType }
                )
            ) { entrada ->
                val cotizacionId = entrada.arguments?.getString(ScreenRoute.Payment.ARGUMENTO)
                // Una renovación en curso se paga con su propia cotización y su monto.
                val renovacion = billetera?.estado?.collectAsState()?.value?.renovacionEnCurso
                    ?.takeIf { it.cotizacionId == cotizacionId }
                val resultado = estadoCotizaciones.resultado?.takeIf { it.cotizacionId == cotizacionId }
                    ?: estadoCotizaciones.listado.firstOrNull { it.cotizacionId == cotizacionId }
                // Una prima pendiente (HU21) trae su propio monto, sin depender de otras pantallas.
                val pendiente = estadoPagos.pendientes.firstOrNull { it.cotizacionId == cotizacionId }
                val monto = renovacion?.primaTotal?.toBigDecimalOrNull()
                    ?: resultado?.primaTotal
                    ?: pendiente?.monto
                val moneda = renovacion?.moneda ?: resultado?.moneda ?: pendiente?.moneda
                if (estado.sesion == null || cotizacionId == null || monto == null || moneda == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    // El pago lleva al portal PSE (pendiente con URL) o a la pantalla de resultado.
                    LaunchedEffect(estadoPagos.pago?.pagoId) {
                        val pago = estadoPagos.pago
                        if (pago != null) {
                            val destino = if (pago.urlRedireccion != null) {
                                ScreenRoute.PsePortal.route
                            } else {
                                ScreenRoute.PaymentResult.route
                            }
                            navController.navigate(destino) { launchSingleTop = true }
                        }
                    }
                    PaymentScreen(
                        cotizacionId = cotizacionId,
                        monto = monto,
                        moneda = moneda,
                        procesando = estadoPagos.procesando,
                        error = estadoPagos.error,
                        onVolver = { navController.popBackStack() },
                        onPagar = { solicitud -> pagos.pagar(solicitud) },
                        onInicio = { navController.popBackStack(ScreenRoute.Home.route, false) },
                        urlRetorno = URL_RETORNO_PSE
                    )
                }
            }

            composable(route = ScreenRoute.PaymentResult.route) {
                val pago = estadoPagos.pago
                val renovacionPagada = billetera?.estado?.collectAsState()?.value?.renovacionEnCurso
                    ?.takeIf { pago != null && it.cotizacionId == pago.cotizacionId }
                val comprobante = estadoPagos.comprobante?.takeIf { pago != null && it.pagoId == pago.pagoId }
                // Una renovación se reconoce por su estado en curso (HU22) o, si el pago se hizo
                // desde "Pagos pendientes" (HU21), por el concepto que informa el backend.
                val esRenovacion = renovacionPagada != null || pago?.concepto == ConceptoPago.RENOVACION
                if (estado.sesion == null || pago == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else if (esRenovacion && pago.estado == EstadoPago.APROBADO) {
                    val polizaId = renovacionPagada?.polizaId
                        ?: comprobante?.polizaId
                        ?: estadoPagos.pendientes.firstOrNull { it.cotizacionId == pago.cotizacionId }?.polizaId
                    // El pago aprobado de una renovación termina en su propia confirmación.
                    RenewalSuccessScreen(
                        comprobanteNumero = comprobante?.numero,
                        onVerPoliza = {
                            pagos.limpiar()
                            billetera?.terminarRenovacion()
                            val enBilletera = navController.popBackStack(ScreenRoute.Wallet.route, false)
                            if (!enBilletera) navController.popBackStack(ScreenRoute.Home.route, false)
                            if (polizaId != null) {
                                navController.navigate(ScreenRoute.Certificate.ruta(polizaId))
                            } else if (!enBilletera && billetera != null) {
                                navController.navigate(ScreenRoute.Wallet.ruta()) { launchSingleTop = true }
                            }
                        },
                        onVolver = {
                            pagos.limpiar()
                            billetera?.terminarRenovacion()
                            navController.popBackStack(ScreenRoute.Home.route, false)
                        },
                        onInicio = {
                            pagos.limpiar()
                            billetera?.terminarRenovacion()
                            navController.popBackStack(ScreenRoute.Home.route, false)
                        },
                        onVerBilletera = billetera?.let {
                            { navController.navigate(ScreenRoute.Wallet.ruta()) { launchSingleTop = true } }
                        }
                    )
                } else {
                    PaymentResultScreen(
                        pago = pago,
                        comprobante = comprobante,
                        onReintentar = {
                            pagos.prepararReintento()
                            navController.popBackStack()
                        },
                        onCerrar = {
                            pagos.limpiar()
                            cotizaciones?.limpiarResultado()
                            navController.popBackStack(ScreenRoute.Home.route, false)
                        },
                        onInicio = {
                            pagos.limpiar()
                            cotizaciones?.limpiarResultado()
                            navController.popBackStack(ScreenRoute.Home.route, false)
                        },
                        onVerBilletera = billetera?.let {
                            { navController.navigate(ScreenRoute.Wallet.ruta()) { launchSingleTop = true } }
                        }
                    )
                }
            }

            composable(route = ScreenRoute.PsePortal.route) {
                val url = estadoPagos.pago?.urlRedireccion
                if (estado.sesion == null || url == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    PsePortalScreen(
                        url = url,
                        urlRetorno = URL_RETORNO_PSE,
                        onRetorno = { pagoId ->
                            pagos.consultar(pagoId)
                            navController.navigate(ScreenRoute.PaymentResult.route) {
                                popUpTo(ScreenRoute.PsePortal.route) { inclusive = true }
                                launchSingleTop = true
                            }
                        },
                        onVolver = { navController.popBackStack() }
                    )
                }
            }

            composable(route = ScreenRoute.Payments.route) {
                if (estado.sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    LaunchedEffect(Unit) {
                        pagos.listar()
                        pagos.cargarPendientes()
                    }
                    PaymentsScreen(
                        pagos = estadoPagos.listado,
                        cargando = estadoPagos.cargandoListado || estadoPagos.cargandoPendientes,
                        error = estadoPagos.errorListado,
                        onReintentar = {
                            pagos.listar()
                            pagos.cargarPendientes()
                        },
                        pendientes = estadoPagos.pendientes,
                        errorPendientes = estadoPagos.errorPendientes,
                        onPagar = { prima ->
                            // Nuevo intento: llave nueva y sin el resultado de un pago anterior.
                            pagos.prepararReintento()
                            navController.navigate(ScreenRoute.Payment.ruta(prima.cotizacionId)) {
                                launchSingleTop = true
                            }
                        },
                        onVerComprobante = { pago -> pagos.verComprobante(pago.pagoId) },
                        comprobanteVisible = estadoPagos.comprobanteVisible,
                        comprobante = estadoPagos.comprobante,
                        errorComprobante = estadoPagos.errorComprobante,
                        onCerrarComprobante = { pagos.cerrarComprobante() },
                        onVolver = { navController.popBackStack() },
                        onInicio = { navController.popBackStack(ScreenRoute.Home.route, false) },
                        onVerBilletera = billetera?.let {
                            { navController.navigate(ScreenRoute.Wallet.ruta()) { launchSingleTop = true } }
                        }
                    )
                }
            }
        }

        if (siniestros != null) {
            composable(
                route = ScreenRoute.ClaimDetail.route,
                arguments = listOf(
                    navArgument(ScreenRoute.ClaimDetail.ARGUMENTO) { type = NavType.StringType }
                )
            ) { entrada ->
                val siniestroId =
                    entrada.arguments?.getString(ScreenRoute.ClaimDetail.ARGUMENTO).orEmpty()
                val estadoSiniestros by siniestros.estado.collectAsState()
                if (estado.sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    // Se pide siempre: al llegar desde una notificación el estado puede haber cambiado.
                    LaunchedEffect(siniestroId) { siniestros.cargar() }
                    PantallaConNavegacion(
                        visible = true,
                        seleccionada = SeccionNavegacion.SINIESTROS,
                        navController = navController,
                        polizasDisponibles = billetera != null,
                        siniestrosDisponibles = true
                    ) { pantallaModifier ->
                        ClaimDetailScreen(
                            siniestro = estadoSiniestros.siniestros?.siniestros
                                ?.firstOrNull { it.siniestroId == siniestroId },
                            cargando = estadoSiniestros.cargando,
                            error = estadoSiniestros.error,
                            onReintentar = { siniestros.cargar() },
                            onVolver = {
                                if (!navController.popBackStack()) {
                                    navController.navigate(ScreenRoute.Home.route) { launchSingleTop = true }
                                }
                            },
                            modifier = pantallaModifier
                        )
                    }
                }
            }

            composable(
                route = ScreenRoute.Claims.route,
                arguments = listOf(
                    navArgument(ScreenRoute.Claims.ORIGEN_NAVBAR) {
                        type = NavType.BoolType
                        defaultValue = false
                    }
                )
            ) { entrada ->
                val desdeNavbar = entrada.arguments?.getBoolean(ScreenRoute.Claims.ORIGEN_NAVBAR) == true
                val estadoSiniestros by siniestros.estado.collectAsState()
                if (estado.sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    // Se vuelve a pedir cada vez que se entra: el backend es la fuente de verdad.
                    LaunchedEffect(Unit) { siniestros.cargar() }
                    PantallaConNavegacion(
                        visible = desdeNavbar,
                        seleccionada = SeccionNavegacion.SINIESTROS,
                        navController = navController,
                        polizasDisponibles = billetera != null,
                        siniestrosDisponibles = true
                    ) { pantallaModifier ->
                        ClaimsScreen(
                            siniestros = estadoSiniestros.siniestros,
                            cargando = estadoSiniestros.cargando,
                            error = estadoSiniestros.error,
                            onReintentar = { siniestros.cargar() },
                            onVolver = { navController.popBackStack() },
                            onVerDetalle = { siniestro ->
                                navController.navigate(ScreenRoute.ClaimDetail.ruta(siniestro.siniestroId)) {
                                    launchSingleTop = true
                                }
                            },
                            onReportar = {
                                navController.navigate(ScreenRoute.ClaimForm.ruta(desdeNavbar)) {
                                    launchSingleTop = true
                                }
                            },
                            modifier = pantallaModifier
                        )
                    }
                }
            }

            composable(
                route = ScreenRoute.ClaimForm.route,
                arguments = listOf(
                    navArgument(ScreenRoute.ClaimForm.ORIGEN_NAVBAR) {
                        type = NavType.BoolType
                        defaultValue = false
                    }
                )
            ) { entrada ->
                val desdeNavbar =
                    entrada.arguments?.getBoolean(ScreenRoute.ClaimForm.ORIGEN_NAVBAR) == true
                val estadoSiniestros by siniestros.estado.collectAsState()
                if (estado.sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    // Las pólizas elegibles son las vigentes de la billetera; si no hay, texto libre.
                    val estadoBilletera = billetera?.estado?.collectAsState()?.value
                    LaunchedEffect(billetera) { billetera?.cargar() }
                    val elegibles = estadoBilletera?.billetera?.vigentes.orEmpty().map { poliza ->
                        com.example.solventa.ui.screens.PolizaElegible(
                            polizaId = poliza.polizaId,
                            etiqueta = "${poliza.nombreRamo} · ${poliza.numeroPoliza}"
                        )
                    }

                    // Al registrar bien, se vuelve a la lista (que ya se recargó en el coordinador).
                    LaunchedEffect(estadoSiniestros.registroExitoso) {
                        if (estadoSiniestros.registroExitoso) {
                            siniestros.consumirRegistroExitoso()
                            navController.popBackStack()
                        }
                    }

                    // HU04: borrador del reporte y captura de evidencias en la carpeta privada.
                    LaunchedEffect(usuarioId) { siniestros.cargarBorrador() }
                    val contexto = LocalContext.current.applicationContext
                    val borradoresArchivo = remember(contexto) {
                        com.example.solventa.data.local.BorradoresSiniestroArchivo(contexto)
                    }
                    val archivosEvidencia = remember(borradoresArchivo) {
                        com.example.solventa.data.local.ArchivosEvidencia(contexto, borradoresArchivo)
                    }
                    val proveedorUbicacion = remember(contexto) {
                        com.example.solventa.data.local.ProveedorUbicacion(contexto)
                    }
                    val accionesEvidencia = rememberCapturaEvidencias(
                        usuarioId = usuarioId,
                        archivos = archivosEvidencia,
                        ubicacion = proveedorUbicacion,
                        onEvidencia = { importada, desdeGaleria ->
                            siniestros.agregarEvidencia(importada, desdeGaleria)
                        }
                    )

                    PantallaConNavegacion(
                        visible = desdeNavbar,
                        seleccionada = SeccionNavegacion.SINIESTROS,
                        navController = navController,
                        polizasDisponibles = billetera != null,
                        siniestrosDisponibles = true
                    ) { pantallaModifier ->
                        ClaimFormScreen(
                            polizas = elegibles,
                            registrando = estadoSiniestros.registrando,
                            error = estadoSiniestros.errorFormulario,
                            onRegistrar = { polizaId, tipo, fecha, hora, lugar, descripcion, estimacion ->
                                siniestros.registrar(
                                    SolicitudSiniestro(
                                        polizaId = polizaId,
                                        fechaEvento = fecha,
                                        horaEvento = if (hora.length == 5) "$hora:00" else hora,
                                        lugar = lugar,
                                        descripcion = descripcion,
                                        estimacionDanos = estimacion,
                                        tipoSiniestro = tipo
                                    )
                                )
                            },
                            onVolver = {
                                siniestros.consumirErrorFormulario()
                                siniestros.consumirAvisoEvidencia()
                                navController.popBackStack()
                            },
                            modifier = pantallaModifier,
                            borrador = estadoSiniestros.borrador,
                            acciones = accionesEvidencia,
                            avisoEvidencia = estadoSiniestros.avisoEvidencia,
                            onQuitarEvidencia = { siniestros.quitarEvidencia(it) },
                            onDescartarBorrador = { siniestros.descartarBorrador() }
                        )
                    }
                }
            }
        }

        if (asesor != null && siniestros != null) {
            composable(
                route = ScreenRoute.AssistedClaimForm.route,
                arguments = listOf(
                    navArgument(ScreenRoute.AssistedClaimForm.ARGUMENTO) { type = NavType.StringType }
                )
            ) { entrada ->
                val clienteId = entrada.arguments
                    ?.getString(ScreenRoute.AssistedClaimForm.ARGUMENTO).orEmpty()
                val estadoAsesor by asesor.estado.collectAsState()
                val estadoSiniestros by siniestros.estado.collectAsState()
                val cliente = estadoAsesor.clienteSeleccionado
                if (estado.sesion == null || cliente == null || cliente.clienteId != clienteId) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    val elegibles = estadoAsesor.polizasCliente?.vigentes.orEmpty().map { poliza ->
                        com.example.solventa.ui.screens.PolizaElegible(
                            polizaId = poliza.polizaId,
                            etiqueta = "${poliza.nombreRamo} · ${poliza.numeroPoliza}"
                        )
                    }

                    // Al registrar bien, se vuelve al inicio del asesor.
                    LaunchedEffect(estadoSiniestros.registroExitoso) {
                        if (estadoSiniestros.registroExitoso) {
                            siniestros.consumirRegistroExitoso()
                            asesor.limpiarSeleccion()
                            navController.popBackStack(ScreenRoute.Home.route, inclusive = false)
                        }
                    }

                    ClaimFormScreen(
                        polizas = elegibles,
                        registrando = estadoSiniestros.registrando,
                        error = estadoSiniestros.errorFormulario,
                        clienteNombre = cliente.nombreCompleto,
                        cargandoPolizas = estadoAsesor.cargandoPolizas,
                        onRegistrar = { polizaId, tipo, fecha, hora, lugar, descripcion, estimacion ->
                            siniestros.registrarAsistido(
                                SolicitudSiniestroAsistido(
                                    clienteId = cliente.clienteId,
                                    polizaId = polizaId,
                                    fechaEvento = fecha,
                                    horaEvento = if (hora.length == 5) "$hora:00" else hora,
                                    lugar = lugar,
                                    descripcion = descripcion,
                                    estimacionDanos = estimacion,
                                    tipoSiniestro = tipo
                                )
                            )
                        },
                        onVolver = {
                            siniestros.consumirErrorFormulario()
                            asesor.limpiarSeleccion()
                            navController.popBackStack()
                        }
                    )
                }
            }
        }

        if (asesor != null) {
            composable(route = ScreenRoute.CreateAdvisor.route) {
                val estadoAsesor by asesor.estado.collectAsState()
                if (estado.sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    CreateAdvisorScreen(
                        creando = estadoAsesor.creandoAsesor,
                        error = estadoAsesor.errorCrearAsesor,
                        creadoNombre = estadoAsesor.asesorCreado?.nombreCompleto,
                        onCrear = { datos: DatosNuevoAsesor ->
                            asesor.consumirErrorCrearAsesor()
                            asesor.crearAsesor(datos)
                        },
                        onVolver = {
                            asesor.consumirErrorCrearAsesor()
                            navController.popBackStack()
                        },
                        onHecho = {
                            asesor.consumirAsesorCreado()
                            navController.popBackStack()
                        }
                    )
                }
            }

            composable(route = ScreenRoute.CreateAuditor.route) {
                val estadoAsesor by asesor.estado.collectAsState()
                if (estado.sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    CreateAuditorScreen(
                        creando = estadoAsesor.creandoAnalista,
                        error = estadoAsesor.errorCrearAnalista,
                        creadoNombre = estadoAsesor.analistaCreado?.nombreCompleto,
                        onCrear = { datos: DatosNuevoAnalista ->
                            asesor.consumirErrorCrearAnalista()
                            asesor.crearAnalista(datos)
                        },
                        onVolver = {
                            asesor.consumirErrorCrearAnalista()
                            navController.popBackStack()
                        },
                        onHecho = {
                            asesor.consumirAnalistaCreado()
                            navController.popBackStack()
                        }
                    )
                }
            }
        }

        if (asistencias != null) {
            composable(route = ScreenRoute.Assistance.route) {
                val sesion = estado.sesion
                if (sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    val estadoAsistencias by asistencias.estado.collectAsState()
                    // Las pólizas elegibles son las vigentes de la billetera; el backend revalida.
                    val estadoBilletera = billetera?.estado?.collectAsState()?.value
                    LaunchedEffect(billetera) { billetera?.cargar() }
                    val elegibles = estadoBilletera?.billetera?.vigentes.orEmpty()
                        .filter { it.ramo == "VIAJE" || it.ramo == "PROTECCION_DISPOSITIVOS" }
                        .map {
                            PolizaAsistenciaElegible(
                                polizaId = it.polizaId,
                                etiqueta = "${it.nombreRamo} · ${it.numeroPoliza}"
                            )
                        }

                    // Pide los permisos de ubicación con las APIs modernas (HU06). Si el cliente
                    // concede alguno, se buscan prestadores; si no, se ofrece "Reintentar".
                    val lanzadorPermiso = rememberLauncherForActivityResult(
                        ActivityResultContracts.RequestMultiplePermissions()
                    ) { concedidos ->
                        if (concedidos.values.any { it }) {
                            asistencias.buscarPrestadores()
                        } else {
                            asistencias.permisoDenegado()
                        }
                    }

                    AssistanceScreen(
                        estado = estadoAsistencias,
                        polizasElegibles = elegibles,
                        tienePermisoUbicacion = asistencias.tienePermisoUbicacion(),
                        onSeleccionarPoliza = { poliza ->
                            asistencias.seleccionarPoliza(poliza.polizaId, poliza.etiqueta)
                        },
                        onSeleccionarServicio = { asistencias.seleccionarServicio(it) },
                        onSolicitarPermiso = {
                            if (asistencias.tienePermisoUbicacion()) {
                                asistencias.buscarPrestadores()
                            } else {
                                lanzadorPermiso.launch(
                                    com.example.solventa.data.local.ProveedorUbicacion.PERMISOS
                                )
                            }
                        },
                        onBuscarPrestadores = { radio -> asistencias.buscarPrestadores(radio) },
                        onSeleccionarPrestador = { asistencias.seleccionarPrestador(it) },
                        onConfirmarSolicitud = { asistencias.solicitar(it) },
                        onVerMisAsistencias = { asistencias.cargarAsistencias() },
                        onCancelarAsistencia = { asistencias.cancelar(it) },
                        onNuevaSolicitud = { asistencias.reiniciarFlujo() },
                        onVolver = {
                            asistencias.consumirError()
                            navController.popBackStack()
                        }
                    )
                }
            }
        }
    }
}

/** URL de retorno que el portal PSE usa para devolver al cliente a la app con ?pago=... */
private const val URL_RETORNO_PSE = "https://solventa.app/pse-retorno"

@Composable
private fun PantallaConNavegacion(
    visible: Boolean,
    seleccionada: SeccionNavegacion,
    navController: NavHostController,
    polizasDisponibles: Boolean,
    siniestrosDisponibles: Boolean,
    contenido: @Composable (Modifier) -> Unit
) {
    Scaffold(
        modifier = Modifier.fillMaxSize(),
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        bottomBar = {
            if (visible) {
                SolventaBottomNavigation(
                    onInicio = {
                        navController.popBackStack(ScreenRoute.Home.route, false)
                    },
                    onPolizas = if (polizasDisponibles) {
                        {
                            navController.navigate(ScreenRoute.Wallet.ruta(desdeNavbar = true)) {
                                popUpTo(ScreenRoute.Home.route)
                                launchSingleTop = true
                            }
                        }
                    } else {
                        null
                    },
                    onSiniestros = if (siniestrosDisponibles) {
                        {
                            navController.navigate(ScreenRoute.Claims.ruta(desdeNavbar = true)) {
                                popUpTo(ScreenRoute.Home.route)
                                launchSingleTop = true
                            }
                        }
                    } else {
                        null
                    },
                    onPerfil = {
                        navController.navigate(ScreenRoute.Profile.route) {
                            popUpTo(ScreenRoute.Home.route)
                            launchSingleTop = true
                        }
                    },
                    seleccionada = seleccionada
                )
            }
        }
    ) { paddingValues ->
        contenido(Modifier.fillMaxSize().padding(paddingValues))
    }
}
