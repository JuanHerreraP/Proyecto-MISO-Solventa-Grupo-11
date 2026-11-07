package com.example.solventa.domain.polizas

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SincronizadorPolizasTest {
    @Test
    fun reintentaConEsperaExponencialHastaTenerExito() = runTest {
        val resultados = ArrayDeque(
            listOf(
                ResultadoSincronizacion.REINTENTAR,
                ResultadoSincronizacion.REINTENTAR,
                ResultadoSincronizacion.EXITO
            )
        )
        val esperas = mutableListOf<Long>()
        var falloPersistente = false
        val sincronizador = SincronizadorPolizas(
            sincronizar = { resultados.removeFirst() },
            alFalloPersistente = { falloPersistente = true },
            esperar = { esperas += it }
        )

        sincronizador.ejecutar()

        assertEquals(listOf(2_000L, 4_000L), esperas)
        assertFalse(falloPersistente)
    }

    @Test
    fun informaSoloDespuesDeAgotarLosIntentos() = runTest {
        var intentos = 0
        var falloPersistente = false
        val sincronizador = SincronizadorPolizas(
            sincronizar = {
                intentos++
                ResultadoSincronizacion.REINTENTAR
            },
            alFalloPersistente = { falloPersistente = true },
            esperar = {}
        )

        sincronizador.ejecutar()

        assertEquals(3, intentos)
        assertTrue(falloPersistente)
    }

    @Test
    fun sinSesionNoReintentaNiInformaFallo() = runTest {
        var intentos = 0
        var falloPersistente = false
        val sincronizador = SincronizadorPolizas(
            sincronizar = {
                intentos++
                ResultadoSincronizacion.SIN_SESION
            },
            alFalloPersistente = { falloPersistente = true },
            esperar = {}
        )

        sincronizador.ejecutar()

        assertEquals(1, intentos)
        assertFalse(falloPersistente)
    }
}
