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
    object QuoteResult : ScreenRoute("quote_result/{ramo}") {
        const val ARGUMENTO = "ramo"
        fun ruta(ramo: RamoCotizacion) = "quote_result/${ramo.codigoApi}"
    }
    object Quotes : ScreenRoute("quotes_screen")
    object QuoteHistoryDetail : ScreenRoute("quote_history/{cotizacionId}") {
        const val ARGUMENTO = "cotizacionId"
        fun ruta(cotizacionId: String) =
            "quote_history/${URLEncoder.encode(cotizacionId, "UTF-8")}"
    }
    object Wallet : ScreenRoute("wallet_screen?desdeNavbar={desdeNavbar}") {
        const val ORIGEN_NAVBAR = "desdeNavbar"
        fun ruta(desdeNavbar: Boolean = false) =
            if (desdeNavbar) "wallet_screen?desdeNavbar=true" else "wallet_screen"
    }
    object Certificate : ScreenRoute("certificate_screen/{polizaId}?desdeNavbar={desdeNavbar}") {
        const val ARGUMENTO = "polizaId"
        const val ORIGEN_NAVBAR = "desdeNavbar"
        fun ruta(polizaId: String, desdeNavbar: Boolean = false): String {
            val base = "certificate_screen/${URLEncoder.encode(polizaId, "UTF-8")}"
            return if (desdeNavbar) "$base?desdeNavbar=true" else base
        }
    }
    object Payment : ScreenRoute("payment_screen/{cotizacionId}") {
        const val ARGUMENTO = "cotizacionId"
        fun ruta(cotizacionId: String) =
            "payment_screen/${URLEncoder.encode(cotizacionId, "UTF-8")}"
    }
    object PsePortal : ScreenRoute("pse_portal_screen")
    object PaymentResult : ScreenRoute("payment_result_screen")
    object Payments : ScreenRoute("payments_screen")
    object Claims : ScreenRoute("claims_screen?desdeNavbar={desdeNavbar}") {
        const val ORIGEN_NAVBAR = "desdeNavbar"
        fun ruta(desdeNavbar: Boolean = false) =
            if (desdeNavbar) "claims_screen?desdeNavbar=true" else "claims_screen"
    }
    object ClaimForm : ScreenRoute("claim_form_screen?desdeNavbar={desdeNavbar}") {
        const val ORIGEN_NAVBAR = "desdeNavbar"
        fun ruta(desdeNavbar: Boolean = false) =
            if (desdeNavbar) "claim_form_screen?desdeNavbar=true" else "claim_form_screen"
    }

    companion object {
        /** Rutas que solo se pueden ver con una sesión activa. */
        val privadas: Set<String>
            get() = setOf(
                Home.route,
                NewQuote.route,
                QuoteForm.route,
                QuoteResult.route,
                Quotes.route,
                QuoteHistoryDetail.route,
                Wallet.route,
                Certificate.route,
                Payment.route,
                PsePortal.route,
                PaymentResult.route,
                Payments.route,
                Claims.route,
                ClaimForm.route
            )
    }
}
