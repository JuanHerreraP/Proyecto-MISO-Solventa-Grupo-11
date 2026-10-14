package com.example.solventa.ui.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.example.solventa.biometric.AutenticadorBiometrico
import com.example.solventa.biometric.DisponibilidadBiometrica
import com.example.solventa.biometric.FalloBiometrico
import com.example.solventa.biometric.mensaje
import com.example.solventa.domain.auth.MensajesAuth
import com.example.solventa.ui.auth.AuthViewModel
import com.example.solventa.ui.screens.BiometricalLoginScreen
import com.example.solventa.ui.screens.CredentialsLoginScreen
import com.example.solventa.ui.screens.HomeScreen
import com.example.solventa.ui.screens.RegisterScreen
import com.example.solventa.ui.screens.WelcomeScreen
import kotlinx.coroutines.delay

@Composable
fun NavGraph(
    viewModel: AuthViewModel,
    autenticador: AutenticadorBiometrico,
    modifier: Modifier = Modifier,
    navController: NavHostController = rememberNavController(),
    startDestination: String = ScreenRoute.Welcome.route
) {
    val estado by viewModel.estado.collectAsState()
    val autenticado = estado.sesion != null

    // Guardia de navegación: con sesión se va al inicio; sin sesión nadie se queda en el inicio.
    LaunchedEffect(autenticado) {
        val actual = navController.currentDestination?.route
        if (autenticado && actual != ScreenRoute.Home.route) {
            navController.navigate(ScreenRoute.Home.route) {
                popUpTo(navController.graph.id) { inclusive = true }
                launchSingleTop = true
            }
        } else if (!autenticado && actual == ScreenRoute.Home.route) {
            navController.navigate(ScreenRoute.BiometricalLogin.route) {
                popUpTo(navController.graph.id) { inclusive = true }
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
                onLoginClick = {
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
                    onCerrarSesion = viewModel::cerrarSesion
                )
            }
        }
    }
}
