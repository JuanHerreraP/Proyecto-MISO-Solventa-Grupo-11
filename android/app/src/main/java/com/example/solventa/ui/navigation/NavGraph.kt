package com.example.solventa.ui.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
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
import com.example.solventa.domain.cotizaciones.CatalogoCotizaciones
import com.example.solventa.domain.cotizaciones.EstadoCotizaciones
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.example.solventa.ui.auth.AuthViewModel
import com.example.solventa.ui.billetera.BilleteraViewModel
import com.example.solventa.ui.billetera.compartirTexto
import com.example.solventa.ui.billetera.textoParaCompartir
import com.example.solventa.ui.cotizaciones.CotizacionesViewModel
import com.example.solventa.ui.screens.BiometricalLoginScreen
import com.example.solventa.ui.screens.CertificateScreen
import com.example.solventa.ui.screens.CredentialsLoginScreen
import com.example.solventa.ui.screens.HomeScreen
import com.example.solventa.ui.screens.NewQuoteScreen
import com.example.solventa.ui.screens.QuoteFormScreen
import com.example.solventa.ui.screens.QuoteResultScreen
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
    cotizaciones: CotizacionesViewModel? = null
) {
    val estado by viewModel.estado.collectAsState()
    val estadoCotizaciones = cotizaciones?.estado?.collectAsState()?.value ?: EstadoCotizaciones()
    val autenticado = estado.sesion != null

    // Guardia de navegación: con sesión se va al inicio; sin sesión nadie se queda en una
    // pantalla privada (inicio, billetera o certificado) y se descarta lo que se cargó.
    LaunchedEffect(autenticado) {
        val actual = navController.currentDestination?.route
        if (!autenticado) {
            billetera?.limpiar()
            cotizaciones?.limpiar()
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
                    onCerrarSesion = viewModel::cerrarSesion,
                    onCotizarSeguro = {
                        navController.navigate(ScreenRoute.NewQuote.route) { launchSingleTop = true }
                    },
                    onVerBilletera = billetera?.let {
                        { navController.navigate(ScreenRoute.Wallet.route) { launchSingleTop = true } }
                    },
                    cantidadPolizasActivas = estadoBilletera?.billetera?.totalVigentes
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
                        { navController.navigate(ScreenRoute.Wallet.route) { launchSingleTop = true } }
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
                        { navController.navigate(ScreenRoute.Wallet.route) { launchSingleTop = true } }
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
                        cotizaciones?.limpiar()
                        navController.popBackStack()
                    },
                    onAceptar = {
                        // La aceptación y compra pertenecen al flujo posterior a HU03.
                    },
                    onCrearOtra = {
                        cotizaciones?.limpiar()
                        navController.popBackStack(ScreenRoute.NewQuote.route, inclusive = false)
                    },
                    onInicio = {
                        cotizaciones?.limpiar()
                        navController.popBackStack(ScreenRoute.Home.route, false)
                    },
                    onVerBilletera = billetera?.let {
                        { navController.navigate(ScreenRoute.Wallet.route) { launchSingleTop = true } }
                    }
                )
            }
        }

        if (billetera != null) {
            composable(route = ScreenRoute.Wallet.route) {
                val estadoBilletera by billetera.estado.collectAsState()
                if (estado.sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    // Se vuelve a pedir cada vez que se entra: el backend es la fuente de verdad.
                    LaunchedEffect(Unit) { billetera.cargar() }
                    WalletScreen(
                        billetera = estadoBilletera.billetera,
                        cargando = estadoBilletera.cargando,
                        error = estadoBilletera.error,
                        onVerPoliza = { polizaId ->
                            navController.navigate(ScreenRoute.Certificate.ruta(polizaId))
                        },
                        onReintentar = billetera::cargar,
                        onVolver = { navController.popBackStack() }
                    )
                }
            }

            composable(
                route = ScreenRoute.Certificate.route,
                arguments = listOf(
                    navArgument(ScreenRoute.Certificate.ARGUMENTO) { type = NavType.StringType }
                )
            ) { entrada ->
                val polizaId = entrada.arguments?.getString(ScreenRoute.Certificate.ARGUMENTO).orEmpty()
                val estadoBilletera by billetera.estado.collectAsState()
                val contexto = LocalContext.current

                if (estado.sesion == null) {
                    Box(modifier = Modifier.fillMaxSize())
                } else {
                    LaunchedEffect(polizaId) { billetera.verCertificado(polizaId) }
                    DisposableEffect(polizaId) { onDispose { billetera.cerrarCertificado() } }

                    LaunchedEffect(estadoBilletera.enlaceParaCompartir) {
                        val enlace = estadoBilletera.enlaceParaCompartir ?: return@LaunchedEffect
                        billetera.enlaceCompartido()
                        contexto.compartirTexto(
                            textoParaCompartir(estadoBilletera.certificado?.numeroPoliza, enlace)
                        )
                    }

                    val certificado = estadoBilletera.certificado?.takeIf { it.polizaId == polizaId }
                    CertificateScreen(
                        certificado = certificado,
                        cargando = estadoBilletera.cargandoCertificado,
                        error = estadoBilletera.errorCertificado,
                        compartiendo = estadoBilletera.compartiendo,
                        mensaje = estadoBilletera.mensaje,
                        onCompartir = { billetera.compartir(polizaId) },
                        onReintentar = { billetera.verCertificado(polizaId) },
                        onVolver = { navController.popBackStack() }
                    )
                }
            }
        }
    }
}
