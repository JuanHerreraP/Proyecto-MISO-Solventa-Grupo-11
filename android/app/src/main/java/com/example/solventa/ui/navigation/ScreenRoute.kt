package com.example.solventa.ui.navigation

sealed class ScreenRoute(val route: String) {
    object Welcome : ScreenRoute("welcome_screen")
    object BiometricalLogin : ScreenRoute("biometrical_login_screen")
    object Register : ScreenRoute("register_screen")
    object CredentialsLogin : ScreenRoute("credentials_login_screen")
    object Home : ScreenRoute("home_screen")
}