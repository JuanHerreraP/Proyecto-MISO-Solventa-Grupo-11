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
            ScreenRoute.CredentialsLogin.route
        )

        assertEquals(
            listOf(
                "welcome_screen",
                "biometrical_login_screen",
                "register_screen",
                "credentials_login_screen"
            ),
            routes
        )
        assertEquals(routes.size, routes.toSet().size)
    }
}
