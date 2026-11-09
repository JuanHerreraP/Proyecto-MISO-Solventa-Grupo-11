package com.example.solventa.ui.screens

import org.junit.Assert.assertEquals
import org.junit.Test

class SyncStatusBannerTest {
    @Test
    fun describeMinutosHorasYDiasDesdeLaUltimaSincronizacion() {
        val ahora = 10_000_000L

        assertEquals("ahora", tiempoTranscurrido(ahora - 30_000L, ahora))
        assertEquals("hace 2 min", tiempoTranscurrido(ahora - 120_000L, ahora))
        assertEquals("hace 2 h", tiempoTranscurrido(ahora - 7_200_000L, ahora))
        assertEquals("hace 2 días", tiempoTranscurrido(ahora - 172_800_000L, ahora))
    }
}
