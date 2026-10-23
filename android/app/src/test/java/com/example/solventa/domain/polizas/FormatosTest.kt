package com.example.solventa.domain.polizas

import java.util.TimeZone
import org.junit.Assert.assertEquals
import org.junit.Test

class FormatosTest {
    private val bogota = TimeZone.getTimeZone("GMT-05:00")

    @Test
    fun fechaIsoEnFormatoCorto() {
        assertEquals("1 oct 2026", Formatos.fecha("2026-10-01"))
        assertEquals("31 dic 2026", Formatos.fecha("2026-12-31"))
    }

    @Test
    fun fechaInvalidaSeDevuelveIgual() {
        assertEquals("mañana", Formatos.fecha("mañana"))
        assertEquals("2026-13-01", Formatos.fecha("2026-13-01"))
    }

    @Test
    fun vigenciaUneInicioYFin() {
        assertEquals("1 oct 2026 – 31 dic 2026", Formatos.vigencia("2026-10-01", "2026-12-31"))
    }

    @Test
    fun fechaHoraSeConvierteALaZonaDelDispositivo() {
        assertEquals("22 oct 2026, 10:00", Formatos.fechaHora("2026-10-22T15:00:00Z", bogota))
        assertEquals("22 oct 2026, 10:00", Formatos.fechaHora("2026-10-22T15:00:00.123456Z", bogota))
        assertEquals("21 oct 2026, 19:30", Formatos.fechaHora("2026-10-22T00:30:00+00:00", bogota))
    }

    @Test
    fun fechaHoraInvalidaSeDevuelveIgual() {
        assertEquals("pronto", Formatos.fechaHora("pronto", bogota))
    }

    @Test
    fun dineroEnPesosSinCentavos() {
        assertEquals("$40.000.000", Formatos.dinero("40000000.00", "COP"))
        assertEquals("$500", Formatos.dinero("500", "COP"))
    }

    @Test
    fun dineroConCentavosYOtraMoneda() {
        assertEquals("$1.234,50", Formatos.dinero("1234.5", "COP"))
        assertEquals("EUR 1.000", Formatos.dinero("1000", "EUR"))
        assertEquals("COP abc", Formatos.dinero("abc", "COP"))
    }

    @Test
    fun estadosEnPalabras() {
        assertEquals("Vigente", Formatos.estado(EstadoPoliza.VIGENTE))
        assertEquals("Vencida", Formatos.estado(EstadoPoliza.VENCIDA))
        assertEquals("Cancelada", Formatos.estado(EstadoPoliza.CANCELADA))
    }
}
