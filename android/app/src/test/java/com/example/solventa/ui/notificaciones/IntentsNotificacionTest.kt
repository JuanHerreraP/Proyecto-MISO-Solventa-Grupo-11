package com.example.solventa.ui.notificaciones

import android.content.Intent
import androidx.test.core.app.ApplicationProvider
import com.example.solventa.MainActivity
import com.example.solventa.domain.notificaciones.DestinoNotificacion
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class IntentsNotificacionTest {

    @Test
    fun unaAperturaDeVencimientoLlevaALaRenovacion() {
        val intent = Intent().putExtra("tipo", "VENCIMIENTO_POLIZA")
            .putExtra("poliza_id", "POL-1")
            .putExtra("notificacion_id", "N-1")

        val apertura = IntentsNotificacion.apertura(intent)

        assertEquals(DestinoNotificacion.Renovacion("POL-1"), apertura?.destino)
        assertEquals("N-1", apertura?.notificacionId)
    }

    @Test
    fun unCambioDeEstadoLlevaAlDetalleDelSiniestro() {
        val intent = Intent().putExtra("tipo", "ESTADO_SINIESTRO").putExtra("siniestro_id", "SIN-1")

        val apertura = IntentsNotificacion.apertura(intent)

        assertEquals(DestinoNotificacion.DetalleSiniestro("SIN-1"), apertura?.destino)
        assertNull(apertura?.notificacionId)
    }

    @Test
    fun sinElIdentificadorNecesarioLlevaALaBandeja() {
        val intent = Intent().putExtra("tipo", "PAGO_PARAMETRICO").putExtra("notificacion_id", " ")

        val apertura = IntentsNotificacion.apertura(intent)

        assertEquals(DestinoNotificacion.Bandeja, apertura?.destino)
        assertNull(apertura?.notificacionId)
    }

    @Test
    fun unIntentQueNoEsDeSolventaSeIgnora() {
        assertNull(IntentsNotificacion.apertura(null))
        assertNull(IntentsNotificacion.apertura(Intent()))
        assertNull(IntentsNotificacion.apertura(Intent().putExtra("tipo", "OTRO")))
        assertNull(IntentsNotificacion.apertura(Intent().putExtra("poliza_id", "POL-1")))
    }

    @Test
    fun elIntentDeLaNotificacionReutilizaLaAppAbierta() {
        val contexto = ApplicationProvider.getApplicationContext<android.content.Context>()

        val intent = IntentsNotificacion.crear(
            contexto,
            mapOf("tipo" to "ESTADO_SINIESTRO", "siniestro_id" to "SIN-1")
        )

        assertEquals(MainActivity::class.java.name, intent.component?.className)
        assertTrue(intent.flags and Intent.FLAG_ACTIVITY_SINGLE_TOP != 0)
        assertTrue(intent.flags and Intent.FLAG_ACTIVITY_CLEAR_TOP != 0)
        // Lo que se manda se puede leer de vuelta como una apertura.
        assertEquals(
            DestinoNotificacion.DetalleSiniestro("SIN-1"),
            IntentsNotificacion.apertura(intent)?.destino
        )
    }
}
