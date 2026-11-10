package com.example.solventa.data.local

import com.example.solventa.domain.siniestros.BorradorSiniestro
import com.example.solventa.domain.siniestros.EvidenciaLocal
import com.example.solventa.domain.siniestros.TipoEvidencia
import com.example.solventa.domain.siniestros.TipoSiniestro
import com.example.solventa.domain.siniestros.Ubicacion
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

/** HU04: borrador del siniestro y archivos de evidencia en el almacenamiento privado. */
class BorradoresSiniestroArchivoTest {

    @get:Rule
    val carpeta = TemporaryFolder()

    private fun almacen() = BorradoresSiniestroArchivo(File(carpeta.root, "borradores_siniestro"))

    private fun evidenciaEn(archivo: File) = EvidenciaLocal(
        id = "E1",
        rutaArchivo = archivo.absolutePath,
        tipoContenido = "image/jpeg",
        tipo = TipoEvidencia.FOTO,
        tamanoBytes = archivo.length(),
        huellaSha256 = ArchivosEvidencia.huellaSha256(archivo),
        capturadaEn = "2026-11-10T15:00:00Z",
        ubicacion = Ubicacion(4.7016, -74.1469, 12f)
    )

    @Test
    fun guardaYLeeElBorradorConSusEvidencias() = runBlocking {
        val almacen = almacen()
        val foto = File(almacen.directorioEvidencias("USR-1"), "foto.jpg").apply {
            writeBytes(byteArrayOf(-1, -40, -1, 1, 2, 3))
        }
        val borrador = BorradorSiniestro(
            id = "B-1",
            polizaId = "POL-1",
            tipoSiniestro = TipoSiniestro.ROBO_HURTO,
            descripcion = "Me robaron el celular en el bus.",
            evidencias = listOf(evidenciaEn(foto)),
            siniestroId = "SIN-9",
            actualizadoEnMs = 42
        )

        almacen.guardar("USR-1", borrador)

        assertEquals(borrador, almacen.leer("USR-1"))
    }

    @Test
    fun cadaUsuarioTieneSuPropioBorrador() = runBlocking {
        val almacen = almacen()
        almacen.guardar("USR-1", BorradorSiniestro(id = "B-1"))

        assertNull(almacen.leer("USR-2"))
        assertEquals("B-1", almacen.leer("USR-1")?.id)
    }

    @Test
    fun laRutaNoContieneElIdentificadorDelUsuario() = runBlocking {
        val almacen = almacen()
        almacen.guardar("ana@correo.com", BorradorSiniestro(id = "B-1"))

        val rutas = carpeta.root.walkTopDown().map { it.path }.toList()
        assertTrue(rutas.none { "ana@correo.com" in it })
    }

    @Test
    fun eliminarBorraElBorradorYSusArchivos() = runBlocking {
        val almacen = almacen()
        val foto = File(almacen.directorioEvidencias("USR-1"), "foto.jpg").apply {
            writeBytes(byteArrayOf(1, 2, 3))
        }
        almacen.guardar("USR-1", BorradorSiniestro(id = "B-1", evidencias = listOf(evidenciaEn(foto))))

        almacen.eliminar("USR-1")

        assertNull(almacen.leer("USR-1"))
        assertFalse(foto.exists())
    }

    @Test
    fun eliminarArchivoSoloBorraArchivosDeLosBorradores() = runBlocking {
        val almacen = almacen()
        val propio = File(almacen.directorioEvidencias("USR-1"), "foto.jpg").apply { writeText("x") }
        val ajeno = carpeta.newFile("otro.jpg").apply { writeText("y") }

        almacen.eliminarArchivo(evidenciaEn(propio))
        almacen.eliminarArchivo(evidenciaEn(ajeno))

        assertFalse(propio.exists())
        assertTrue(ajeno.exists())
    }

    @Test
    fun unBorradorIlegibleSeDescarta() = runBlocking {
        val almacen = almacen()
        almacen.guardar("USR-1", BorradorSiniestro(id = "B-1"))
        val archivo = carpeta.root.walkTopDown().first { it.name == "borrador.json" }
        archivo.writeText("{no es json")

        assertNull(almacen.leer("USR-1"))
        assertFalse(archivo.exists())
    }

    @Test
    fun copiaConTopeYHuella() {
        val salida = ByteArrayOutputStream()
        val copiados = ArchivosEvidencia.copiarConLimite(
            ByteArrayInputStream(ByteArray(300_000)),
            salida,
            limite = 100_000
        )
        // Se detiene apenas supera el tope: el archivo se rechaza sin copiarlo completo.
        assertTrue(copiados > 100_000)
        assertTrue(copiados < 300_000)

        val pequeno = ArchivosEvidencia.copiarConLimite(
            ByteArrayInputStream(ByteArray(10)),
            ByteArrayOutputStream(),
            limite = 100
        )
        assertEquals(10L, pequeno)

        val archivo = carpeta.newFile("hola.txt").apply { writeText("hola") }
        assertEquals(
            "b221d9dbb083a7f33428d7c2a3c3198ae925614d70210e28716ccaa7cd4ddb79",
            ArchivosEvidencia.huellaSha256(archivo)
        )
    }

    @Test
    fun fechaDeCapturaEnIsoUtc() {
        assertEquals("2026-11-10T20:00:00Z", ArchivosEvidencia.isoUtc(1_794_340_800_000L))
    }
}
