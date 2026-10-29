package com.example.solventa.domain.polizas

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CondicionParametricaTest {

    private val condicion =
        "tipo_evento=RETRASO_VUELO; numero_vuelo=AV123; ubicacion=BOG; " +
            "umbral_disparo=180; unidad=MINUTOS"

    @Test
    fun parsearDevuelveLosPares() {
        val mapa = CondicionParametrica.parsear(condicion)
        assertEquals("RETRASO_VUELO", mapa["tipo_evento"])
        assertEquals("AV123", mapa["numero_vuelo"])
        assertEquals("BOG", mapa["ubicacion"])
        assertEquals("180", mapa["umbral_disparo"])
    }

    @Test
    fun parsearToleraVacioYNull() {
        assertTrue(CondicionParametrica.parsear(null).isEmpty())
        assertTrue(CondicionParametrica.parsear("").isEmpty())
        assertTrue(CondicionParametrica.parsear("   ").isEmpty())
    }

    @Test
    fun camposUsaEtiquetasAmigablesYNoDuplicaElTipoDeEvento() {
        val campos = CondicionParametrica.campos(condicion)
        // tipo_evento no se muestra (ya está en el nombre de la cobertura): no se duplica.
        assertEquals(
            listOf("Número de vuelo", "Ubicación", "Umbral de activación", "Unidad"),
            campos.map { it.etiqueta }
        )
        assertEquals("AV123", campos[0].valor)
        assertEquals("BOG", campos[1].valor)
        assertEquals("minutos", campos[3].valor)
    }

    @Test
    fun valorAseguradoSeMarcaComoMoneda() {
        val campos = CondicionParametrica.campos("valor_asegurado=500000; ubicacion=BOG")
        val valorAsegurado = campos.first { it.etiqueta == "Valor asegurado" }
        assertTrue(valorAsegurado.esMoneda)
        val ubicacion = campos.first { it.etiqueta == "Ubicación" }
        assertTrue(!ubicacion.esMoneda)
    }

    @Test
    fun camposIncluyeClavesNoPrevistasAlFinal() {
        val campos = CondicionParametrica.campos("ubicacion=BOG; extra_raro=hola")
        assertEquals("Ubicación", campos[0].etiqueta)
        assertEquals("Extra raro", campos[1].etiqueta)
        assertEquals("hola", campos[1].valor)
    }

    @Test
    fun camposVacioSiNoHayDescripcion() {
        assertTrue(CondicionParametrica.campos(null).isEmpty())
    }
}
