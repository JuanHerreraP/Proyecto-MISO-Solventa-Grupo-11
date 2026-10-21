package com.example.solventa.ui.navigation

import org.junit.Assert.assertEquals
import org.junit.Test

class ScreenRouteTest {
    @Test
    fun routesHaveStableUniqueIdentifiers() {
        val routes = listOf(
            ScreenRoute.Welcome.route,
            ScreenRoute.BiometricalLogin.route,
            ScreenRoute.Register.route,
            ScreenRoute.CredentialsLogin.route,
            ScreenRoute.Home.route,
            ScreenRoute.Wallet.route,
            ScreenRoute.Certificate.route
        )

        assertEquals(
            listOf(
                "welcome_screen",
                "biometrical_login_screen",
                "register_screen",
                "credentials_login_screen",
                "home_screen",
                "wallet_screen",
                "certificate_screen/{polizaId}"
            ),
            routes
        )
        assertEquals(routes.size, routes.toSet().size)
    }

    @Test
    fun laRutaDelCertificadoLlevaElIdCodificado() {
        assertEquals("certificate_screen/POL-1", ScreenRoute.Certificate.ruta("POL-1"))
        assertEquals("certificate_screen/a%2Fb", ScreenRoute.Certificate.ruta("a/b"))
    }

    @Test
    fun lasRutasPrivadasIncluyenCotizacionBilleteraYCertificado() {
        assertEquals(
            setOf(
                "home_screen",
                "new_quote_screen",
                "wallet_screen",
                "certificate_screen/{polizaId}"
            ),
            ScreenRoute.privadas
        )
    }
}
