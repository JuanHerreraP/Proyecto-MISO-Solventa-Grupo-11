package com.example.solventa.ui.components

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CodigoQrTest {
    @Test
    fun generaUnaMatrizCuadradaConLosPatronesDePosicion() {
        val matriz = checkNotNull(matrizQr("SOLVENTA|SOL-VJ-0001|a1b2c3d4e5f60718"))

        assertTrue(matriz.size >= 21)
        assertTrue(matriz.all { it.size == matriz.size })
        // Con margen 1, la esquina del patrón de posición superior izquierdo está en (1, 1).
        assertTrue(matriz[1][1])
        assertTrue(matriz[1][matriz.size - 2])
        assertTrue(matriz[matriz.size - 2][1])
    }

    @Test
    fun elMismoContenidoDaElMismoQrYOtroContenidoOtro() {
        val uno = matrizQr("SOLVENTA|A|1")
        assertEquals(uno, matrizQr("SOLVENTA|A|1"))
        assertNotEquals(uno, matrizQr("SOLVENTA|B|2"))
    }

    @Test
    fun contenidoVacioNoGeneraQr() {
        assertNull(matrizQr(""))
        assertNotNull(matrizQr("x"))
    }
}
