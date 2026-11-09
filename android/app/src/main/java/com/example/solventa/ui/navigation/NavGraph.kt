package com.example.solventa.ui.navigation

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
import com.example.solventa.ui.pagos.PagosViewModel
import com.example.solventa.ui.siniestros.SiniestrosViewModel
import com.example.solventa.ui.screens.AdvisorHomeScreen
import com.example.solventa.ui.screens.BiometricalLoginScreen
import com.example.solventa.ui.screens.CertificateScreen
import com.example.solventa.ui.screens.ClaimFormScreen
import com.example.solventa.ui.screens.ClaimsScreen
import com.example.solventa.ui.screens.CreateAdvisorScreen
import com.example.solventa.ui.screens.CreateAuditorScreen
import com.example.solventa.ui.screens.CredentialsLoginScreen
import com.example.solventa.ui.screens.HomeScreen
import com.example.solventa.ui.screens.NewQuoteScreen
import com.example.solventa.ui.screens.PaymentResultScreen
import com.example.solventa.ui.screens.PaymentScreen
import com.example.solventa.ui.screens.PaymentsScreen
import com.example.solventa.ui.screens.PolicyHistoryScreen
import com.example.solventa.ui.screens.PsePortalScreen
import com.example.solventa.ui.screens.QuoteFormScreen
import com.example.solventa.ui.screens.QuoteResultScreen
import com.example.solventa.ui.screens.QuotesScreen
import com.example.solventa.ui.screens.RegisterScreen
import com.example.solventa.ui.screens.WalletScreen
import com.example.solventa.ui.screens.WelcomeScreen
import kotlinx.coroutines.delay

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
    asesor: AsesorViewModel? = null
) {
    val estado by viewModel.estado.collectAsState()
    val estadoCotizaciones = cotizaciones?.estado?.collectAsState()?.value ?: EstadoCotizaciones()
    val estadoPagos = pagos?.estado?.collectAsState()?.value ?: EstadoPagos()
    val autenticado = estado.sesion != null
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

                HomeScreen(
                    perfil = sesion.perfil,
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
                    onCerrarSesion = {
                        // Inicia el borrado inmediatamente; la guardia también lo confirma
                        // cuando observe que la sesión quedó cerrada.
                        billetera?.eliminarDatosLocales()
                        viewModel.cerrarSesion()
                    },
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
                            // La aceptación pertenece al siguiente paso del flujo de compra.
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

        if (pagos != null) {
            composable(
                route = ScreenRoute.Payment.route,
                arguments = listOf(
                    navArgument(ScreenRoute.Payment.ARGUMENTO) { type = NavType.StringType }
                )
            ) { entrada ->
                val cotizacionId = entrada.arguments?.getString(ScreenRoute.Payment.ARGUMENTO)
                val resultado = estadoCotizaciones.resultado
                    ?: estadoCotizaciones.listado.firstOrNull { it.cotizacionId == cotizacionId }
                if (estado.sesion == null || cotizacionId == null || resultado == null) {
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
                        monto = resultado.primaTotal,
                        moneda = resultado.moneda,
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
                if (estado.sesion == null || pago == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    PaymentResultScreen(
                        pago = pago,
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
                    LaunchedEffect(Unit) { pagos.listar() }
                    PaymentsScreen(
                        pagos = estadoPagos.listado,
                        cargando = estadoPagos.cargandoListado,
                        error = estadoPagos.errorListado,
                        onReintentar = { pagos.listar() },
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
                            onRegistrar = { polizaId, fecha, hora, lugar, descripcion, estimacion ->
                                siniestros.registrar(
                                    SolicitudSiniestro(
                                        polizaId = polizaId,
                                        fechaEvento = fecha,
                                        horaEvento = if (hora.length == 5) "$hora:00" else hora,
                                        lugar = lugar,
                                        descripcion = descripcion,
                                        estimacionDanos = estimacion
                                    )
                                )
                            },
                            onVolver = {
                                siniestros.consumirErrorFormulario()
                                navController.popBackStack()
                            },
                            modifier = pantallaModifier
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
                        onRegistrar = { polizaId, fecha, hora, lugar, descripcion, estimacion ->
                            siniestros.registrarAsistido(
                                SolicitudSiniestroAsistido(
                                    clienteId = cliente.clienteId,
                                    polizaId = polizaId,
                                    fechaEvento = fecha,
                                    horaEvento = if (hora.length == 5) "$hora:00" else hora,
                                    lugar = lugar,
                                    descripcion = descripcion,
                                    estimacionDanos = estimacion
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
                    seleccionada = seleccionada
                )
            }
        }
    ) { paddingValues ->
        contenido(Modifier.fillMaxSize().padding(paddingValues))
    }
}
