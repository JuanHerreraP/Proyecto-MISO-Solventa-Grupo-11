package com.example.solventa.domain.polizas

import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CachePolizasTest {
    private val diaMs = 24L * 60L * 60L * 1_000L

    @Test
    fun datosDeUsuariosDistintosTienenClavesDistintas() {
        assertNotEquals(ClaveUsuarioCache("usuario-a"), ClaveUsuarioCache("usuario-b"))
    }

    @Test(expected = IllegalArgumentException::class)
    fun noPermiteUnaClaveDeUsuarioVacia() {
        ClaveUsuarioCache("   ")
    }

    @Test
    fun aLosTreintaDiasLosDatosAunNoSeConsideranAntiguos() {
        val metadatos = MetadatosSincronizacion(
            usuario = ClaveUsuarioCache("usuario-a"),
            sincronizadaEnMs = 1_000L
        )

        assertFalse(metadatos.superaAntiguedadMaxima(1_000L + 30L * diaMs))
    }

    @Test
    fun despuesDeTreintaDiasLosDatosSeConsideranAntiguos() {
        val metadatos = MetadatosSincronizacion(
            usuario = ClaveUsuarioCache("usuario-a"),
            sincronizadaEnMs = 1_000L
        )

        assertTrue(metadatos.superaAntiguedadMaxima(1_001L + 30L * diaMs))
    }

    @Test
    fun unaFechaDelDispositivoAnteriorALaSincronizacionNoMarcaDatosAntiguos() {
        val metadatos = MetadatosSincronizacion(
            usuario = ClaveUsuarioCache("usuario-a"),
            sincronizadaEnMs = 10_000L
        )

        assertFalse(metadatos.superaAntiguedadMaxima(5_000L))
    }
}
