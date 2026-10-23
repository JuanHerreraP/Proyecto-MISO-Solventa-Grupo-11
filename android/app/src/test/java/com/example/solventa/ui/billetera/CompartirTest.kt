package com.example.solventa.ui.billetera

import com.example.solventa.domain.polizas.EnlaceCompartido
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CompartirTest {
    private val url = "https://api.solventa.co/api/v1/certificados-compartidos/abc"

    @Test
    fun elTextoIncluyeLaPolizaElEnlaceYSuVencimiento() {
        val texto = textoParaCompartir("SOL-VJ-0001", EnlaceCompartido(url, "2026-10-22T15:00:00Z"))

        assertTrue(texto.startsWith("Certificado de mi póliza SOL-VJ-0001 en Solventa: $url"))
        assertTrue(texto.contains("válido hasta el"))
    }

    @Test
    fun sinNumeroNiVencimientoSoloVaElEnlace() {
        assertEquals(
            "Certificado de mi póliza en Solventa: $url",
            textoParaCompartir(null, EnlaceCompartido(url, ""))
        )
    }
}
