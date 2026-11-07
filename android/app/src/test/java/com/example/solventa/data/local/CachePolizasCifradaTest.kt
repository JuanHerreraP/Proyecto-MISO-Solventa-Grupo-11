package com.example.solventa.data.local

import com.example.solventa.domain.polizas.ClaveUsuarioCache
import com.example.solventa.domain.polizas.billeteraDe
import com.example.solventa.domain.polizas.certificado
import com.example.solventa.domain.polizas.resumen
import javax.crypto.KeyGenerator
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CachePolizasCifradaTest {
    private val almacen = AlmacenMemoria()
    private val llave = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()
    private val cache = CachePolizasCifrada(almacen, llave)
    private val ana = ClaveUsuarioCache("usuario-ana")
    private val juan = ClaveUsuarioCache("usuario-juan")

    @Test
    fun guardaYRecuperaLaBilleteraYElCertificado() = runTest {
        val billetera = billeteraDe(resumen())
        val certificado = certificado()

        cache.reemplazar(ana, billetera, listOf(certificado), 123_456L)

        assertEquals(billetera, cache.billetera(ana)?.billetera)
        assertEquals(123_456L, cache.billetera(ana)?.metadatos?.sincronizadaEnMs)
        assertEquals(certificado, cache.certificado(ana, "POL-1")?.certificado)
    }

    @Test
    fun nuncaPersisteDatosSensiblesEnTextoClaro() = runTest {
        cache.reemplazar(ana, billeteraDe(resumen()), listOf(certificado()), 123_456L)

        val persistido = almacen.valores.entries.single()
        assertFalse(persistido.key.contains("usuario-ana"))
        assertFalse(persistido.value.contains("SOL-VJ-0001"))
        assertFalse(persistido.value.contains("Ana Pérez"))
        assertFalse(persistido.value.contains("usuario-ana"))
    }

    @Test
    fun aislaLaInformacionDeCadaUsuario() = runTest {
        cache.reemplazar(ana, billeteraDe(resumen(id = "POL-ANA")), emptyList(), 1L)

        assertNull(cache.billetera(juan))

        cache.reemplazar(juan, billeteraDe(resumen(id = "POL-JUAN")), emptyList(), 2L)
        assertEquals("POL-ANA", cache.billetera(ana)?.billetera?.polizas?.single()?.polizaId)
        assertEquals("POL-JUAN", cache.billetera(juan)?.billetera?.polizas?.single()?.polizaId)
    }

    @Test
    fun reemplazarDescartaCertificadosDeLaSincronizacionAnterior() = runTest {
        cache.reemplazar(ana, billeteraDe(resumen()), listOf(certificado()), 1L)
        cache.reemplazar(ana, billeteraDe(resumen()), emptyList(), 2L)

        assertNull(cache.certificado(ana, "POL-1"))
        assertEquals(2L, cache.billetera(ana)?.metadatos?.sincronizadaEnMs)
    }

    @Test
    fun eliminarUnUsuarioConservaLosDatosDelOtro() = runTest {
        cache.reemplazar(ana, billeteraDe(resumen(id = "POL-ANA")), emptyList(), 1L)
        cache.reemplazar(juan, billeteraDe(resumen(id = "POL-JUAN")), emptyList(), 1L)

        cache.eliminar(ana)

        assertNull(cache.billetera(ana))
        assertTrue(cache.billetera(juan) != null)
    }

    @Test
    fun contenidoAlteradoSeDescartaSinExponerDatos() = runTest {
        cache.reemplazar(ana, billeteraDe(resumen()), emptyList(), 1L)
        val clave = almacen.valores.keys.single()
        almacen.valores[clave] = almacen.valores.getValue(clave).replaceFirst("a", "b")

        assertNull(cache.billetera(ana))
        assertTrue(almacen.valores.isEmpty())
    }

    @Test(expected = IllegalArgumentException::class)
    fun rechazaUnCertificadoQueNoPerteneceALaBilletera() = runTest {
        cache.reemplazar(
            ana,
            billeteraDe(resumen(id = "POL-1")),
            listOf(certificado(id = "POL-AJENA")),
            1L
        )
    }

    @Test
    fun eliminarTodoBorraTodasLasInstantaneas() = runTest {
        cache.reemplazar(ana, billeteraDe(resumen()), emptyList(), 1L)
        cache.reemplazar(juan, billeteraDe(resumen()), emptyList(), 1L)

        cache.eliminarTodo()

        assertTrue(almacen.valores.isEmpty())
    }
}

private class AlmacenMemoria : AlmacenCachePolizas {
    val valores = mutableMapOf<String, String>()

    override fun guardar(clave: String, valor: String) {
        valores[clave] = valor
    }

    override fun leer(clave: String): String? = valores[clave]

    override fun eliminar(clave: String) {
        valores.remove(clave)
    }

    override fun eliminarTodo() {
        valores.clear()
    }
}
