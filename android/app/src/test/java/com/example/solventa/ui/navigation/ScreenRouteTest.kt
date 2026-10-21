package com.example.solventa.ui.navigation

import com.example.solventa.domain.cotizaciones.RamoCotizacion
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
            ScreenRoute.NewQuote.route,
            ScreenRoute.QuoteForm.route,
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
                "new_quote_screen",
                "quote_form/{ramo}",
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
    fun laRutaDelFormularioIncluyeElCodigoDelRamo() {
        assertEquals(
            "quote_form/PROTECCION_DISPOSITIVOS",
            ScreenRoute.QuoteForm.ruta(RamoCotizacion.DISPOSITIVOS)
        )
    }

    @Test
    fun lasRutasPrivadasIncluyenCotizacionBilleteraYCertificado() {
        assertEquals(
            setOf(
                "home_screen",
                "new_quote_screen",
                "quote_form/{ramo}",
                "wallet_screen",
                "certificate_screen/{polizaId}"
            ),
            ScreenRoute.privadas
        )
    }
}
