package com.example.solventa.ui.navigation

import java.net.URLEncoder

import com.example.solventa.domain.cotizaciones.RamoCotizacion

sealed class ScreenRoute(val route: String) {
    object Welcome : ScreenRoute("welcome_screen")
    object BiometricalLogin : ScreenRoute("biometrical_login_screen")
    object Register : ScreenRoute("register_screen")
    object CredentialsLogin : ScreenRoute("credentials_login_screen")
    object Home : ScreenRoute("home_screen")
    object NewQuote : ScreenRoute("new_quote_screen")
    object QuoteForm : ScreenRoute("quote_form/{ramo}") {
        const val ARGUMENTO = "ramo"
        fun ruta(ramo: RamoCotizacion) = "quote_form/${ramo.codigoApi}"
    }
    object Wallet : ScreenRoute("wallet_screen")
    object Certificate : ScreenRoute("certificate_screen/{polizaId}") {
        const val ARGUMENTO = "polizaId"
        fun ruta(polizaId: String) = "certificate_screen/${URLEncoder.encode(polizaId, "UTF-8")}"
    }

    companion object {
        /** Rutas que solo se pueden ver con una sesión activa. */
        val privadas: Set<String>
            get() = setOf(
                Home.route,
                NewQuote.route,
                QuoteForm.route,
                Wallet.route,
                Certificate.route
            )
    }
}
