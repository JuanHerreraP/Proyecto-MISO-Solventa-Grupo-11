package com.example.solventa.ui.validation

import java.util.Calendar
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** HU20: validación del formulario de registro manual de siniestros. */
class SiniestroFormValidationTest {

    private fun hoy(anio: Int, mes1a12: Int, dia: Int): Calendar =
        Calendar.getInstance().apply { set(anio, mes1a12 - 1, dia, 12, 0, 0) }

    @Test
    fun polizaVaciaEsError() {
        assertEquals("Selecciona o ingresa la póliza afectada.", errorPolizaSiniestro("  "))
        assertNull(errorPolizaSiniestro("POL-1"))
    }

    @Test
    fun lugarValidoYLimites() {
        assertEquals("Ingresa el lugar del evento.", errorLugarSiniestro(""))
        assertEquals("Máximo 200 caracteres.", errorLugarSiniestro("x".repeat(201)))
        assertNull(errorLugarSiniestro("Aeropuerto El Dorado"))
    }

    @Test
    fun descripcionExigeAlMenosDiezCaracteres() {
        assertEquals("Describe lo que pasó.", errorDescripcionSiniestro(""))
        assertTrue(errorDescripcionSiniestro("corta") != null)
        assertNull(errorDescripcionSiniestro("Descripción suficientemente larga."))
        assertEquals("Máximo 2000 caracteres.", errorDescripcionSiniestro("a".repeat(2001)))
    }

    @Test
    fun estimacionAceptaDecimalNoNegativo() {
        assertEquals("Ingresa una estimación del daño.", errorEstimacionSiniestro(""))
        assertNull(errorEstimacionSiniestro("850000"))
        assertNull(errorEstimacionSiniestro("850000.50"))
        assertNull(errorEstimacionSiniestro("850000,50"))
        assertTrue(errorEstimacionSiniestro("-5") != null)
        assertTrue(errorEstimacionSiniestro("abc") != null)
        assertTrue(errorEstimacionSiniestro("1.234") != null) // más de 2 decimales
    }

    @Test
    fun horaExigeFormato24h() {
        assertEquals("Ingresa la hora del evento.", errorHoraSiniestro(""))
        assertNull(errorHoraSiniestro("18:30"))
        assertNull(errorHoraSiniestro("00:00"))
        assertNull(errorHoraSiniestro("23:59"))
        assertTrue(errorHoraSiniestro("24:00") != null)
        assertTrue(errorHoraSiniestro("9:5") != null)
    }

    @Test
    fun fechaNoPuedeSerFutura() {
        val hoy = hoy(2026, 10, 26)
        assertEquals("Selecciona la fecha del evento.", errorFechaSiniestro("", hoy))
        assertEquals("Usa el formato AAAA-MM-DD.", errorFechaSiniestro("26/10/2026", hoy))
        assertNull(errorFechaSiniestro("2026-10-26", hoy))
        assertNull(errorFechaSiniestro("2026-10-20", hoy))
        assertEquals("La fecha no puede estar en el futuro.", errorFechaSiniestro("2026-10-27", hoy))
    }

    @Test
    fun normalizarEstimacionUsaPunto() {
        assertEquals("850000.50", normalizarEstimacion(" 850000,50 "))
        assertEquals("1000", normalizarEstimacion("1000"))
    }

    @Test
    fun formularioCompletoValido() {
        assertTrue(
            esFormularioSiniestroValido(
                polizaId = "POL-1",
                fecha = "2020-05-10",
                hora = "18:30",
                lugar = "El Dorado",
                descripcion = "El vuelo fue cancelado.",
                estimacion = "850000"
            )
        )
    }

    @Test
    fun formularioInvalidoSiFaltaAlgo() {
        assertFalse(
            esFormularioSiniestroValido(
                polizaId = "",
                fecha = "2020-05-10",
                hora = "18:30",
                lugar = "El Dorado",
                descripcion = "El vuelo fue cancelado.",
                estimacion = "850000"
            )
        )
    }
}
