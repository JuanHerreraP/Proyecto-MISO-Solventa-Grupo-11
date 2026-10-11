package com.example.solventa.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.example.solventa.ui.screens.WelcomeScreen
import com.example.solventa.ui.screens.BiometricalLoginScreen
import com.example.solventa.ui.screens.CredentialsLoginScreen



@Composable
fun NavGraph(
    modifier: Modifier = Modifier,
    navController: NavHostController = rememberNavController(),
    startDestination: String = ScreenRoute.Welcome.route
) {
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
            BiometricalLoginScreen(
                onUseCredentialsClick = {
                    navController.navigate(ScreenRoute.CredentialsLogin.route)
                },
                onBackClick = {
                    navController.popBackStack()
                }
            )
        }

        composable(route = ScreenRoute.CredentialsLogin.route) {
            CredentialsLoginScreen(
                onBackClick = {
                    navController.popBackStack()
                }
            )
        }

    }
}