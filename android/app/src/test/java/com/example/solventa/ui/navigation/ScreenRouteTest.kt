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
            ScreenRoute.QuoteResult.route,
            ScreenRoute.Quotes.route,
            ScreenRoute.QuoteHistoryDetail.route,
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
                "quote_result/{ramo}",
                "quotes_screen",
                "quote_history/{cotizacionId}",
                "wallet_screen?desdeNavbar={desdeNavbar}",
                "certificate_screen/{polizaId}?desdeNavbar={desdeNavbar}"
            ),
            routes
        )
        assertEquals(routes.size, routes.toSet().size)
    }

    @Test
    fun laRutaDelCertificadoLlevaElIdCodificado() {
        assertEquals("certificate_screen/POL-1", ScreenRoute.Certificate.ruta("POL-1"))
        assertEquals("certificate_screen/a%2Fb", ScreenRoute.Certificate.ruta("a/b"))
        assertEquals(
            "certificate_screen/POL-1?desdeNavbar=true",
            ScreenRoute.Certificate.ruta("POL-1", desdeNavbar = true)
        )
    }

    @Test
    fun lasSeccionesConservanElOrigenDelNavbar() {
        assertEquals("wallet_screen", ScreenRoute.Wallet.ruta())
        assertEquals("wallet_screen?desdeNavbar=true", ScreenRoute.Wallet.ruta(desdeNavbar = true))
        assertEquals("claims_screen", ScreenRoute.Claims.ruta())
        assertEquals("claims_screen?desdeNavbar=true", ScreenRoute.Claims.ruta(desdeNavbar = true))
        assertEquals("claim_form_screen", ScreenRoute.ClaimForm.ruta())
        assertEquals(
            "claim_form_screen?desdeNavbar=true",
            ScreenRoute.ClaimForm.ruta(desdeNavbar = true)
        )
    }

    @Test
    fun laRutaDelFormularioIncluyeElCodigoDelRamo() {
        assertEquals(
            "quote_form/PROTECCION_DISPOSITIVOS",
            ScreenRoute.QuoteForm.ruta(RamoCotizacion.DISPOSITIVOS)
        )
    }

    @Test
    fun laRutaDelResultadoIncluyeElCodigoDelRamo() {
        assertEquals(
            "quote_result/VIDA",
            ScreenRoute.QuoteResult.ruta(RamoCotizacion.VIDA)
        )
    }

    @Test
    fun laRutaDelDetalleLlevaElIdDeLaCotizacion() {
        assertEquals("quote_history/COT-1", ScreenRoute.QuoteHistoryDetail.ruta("COT-1"))
    }

    @Test
    fun lasRutasPrivadasIncluyenCotizacionBilleteraYCertificado() {
        assertEquals(
            setOf(
                "home_screen",
                "new_quote_screen",
                "quote_form/{ramo}",
                "quote_result/{ramo}",
                "quotes_screen",
                "quote_history/{cotizacionId}",
                "wallet_screen?desdeNavbar={desdeNavbar}",
                "certificate_screen/{polizaId}?desdeNavbar={desdeNavbar}",
                "renewal_screen/{polizaId}?desdeNavbar={desdeNavbar}",
                "cancel_screen/{polizaId}?desdeNavbar={desdeNavbar}",
                "payment_screen/{cotizacionId}",
                "pse_portal_screen",
                "payment_result_screen",
                "payments_screen",
                "claims_screen?desdeNavbar={desdeNavbar}",
                "claim_form_screen?desdeNavbar={desdeNavbar}"
            ),
            ScreenRoute.privadas
        )
    }
}
