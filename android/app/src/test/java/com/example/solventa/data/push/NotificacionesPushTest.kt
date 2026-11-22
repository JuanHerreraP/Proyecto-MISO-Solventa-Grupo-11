package com.example.solventa.data.push

import android.Manifest
import android.app.Application
import android.app.NotificationManager
import android.content.Context
import android.os.Bundle
import androidx.test.core.app.ApplicationProvider
import com.example.solventa.domain.notificaciones.DestinoNotificacion
import com.example.solventa.ui.notificaciones.IntentsNotificacion
import com.google.firebase.messaging.RemoteMessage
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf

/** HU05: el canal de Android y el servicio que muestra el push con la app abierta. */
@RunWith(RobolectricTestRunner::class)
class NotificacionesPushTest {

    private val contexto: Application = ApplicationProvider.getApplicationContext()
    private val gestor get() = contexto.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

    @Before
    fun permitir() {
        shadowOf(contexto).grantPermissions(Manifest.permission.POST_NOTIFICATIONS)
    }

    @After
    fun limpiar() {
        NuevoTokenPush.alRecibir = null
    }

    private fun mensaje(
        conAviso: Boolean = true,
        datos: Map<String, String> = mapOf(
            "tipo" to "ESTADO_SINIESTRO",
            "siniestro_id" to "SIN-1",
            "notificacion_id" to "N-1"
        )
    ): RemoteMessage {
        val extras = Bundle()
        if (conAviso) {
            extras.putString("gcm.n.e", "1")
            extras.putString("gcm.notification.title", "Tu siniestro está en evaluación")
            extras.putString("gcm.notification.body", "Estamos evaluando tu siniestro.")
            extras.putString("gcm.notification.tag", "ESTADO_SINIESTRO:2026-11-21")
        }
        datos.forEach { (clave, valor) -> extras.putString(clave, valor) }
        return RemoteMessage(extras)
    }

    private fun servicio() = Robolectric.setupService(SolventaMessagingService::class.java)

    @Test
    fun elCanalSeCreaUnaVezConElMismoIdQueUsaElBackend() {
        CanalNotificaciones.crear(contexto)
        CanalNotificaciones.crear(contexto)

        assertEquals("solventa_notificaciones", CanalNotificaciones.ID)
        assertNotNull(gestor.getNotificationChannel("solventa_notificaciones"))
    }

    @Test
    fun conLaAppAbiertaElPushSeMuestraEnElCanalYAbreElDestino() {
        servicio().onMessageReceived(mensaje())

        val mostrada = shadowOf(gestor).allNotifications.single()
        assertEquals("solventa_notificaciones", mostrada.channelId)
        assertEquals("Tu siniestro está en evaluación", mostrada.extras.getString("android.title"))
        assertEquals("Estamos evaluando tu siniestro.", mostrada.extras.getString("android.text"))
        assertNotNull(mostrada.contentIntent)
        assertNotNull(shadowOf(gestor).getNotification("ESTADO_SINIESTRO:2026-11-21", 1))
    }

    @Test
    fun otroPushDelMismoGrupoReemplazaAlAnterior() {
        val servicio = servicio()

        servicio.onMessageReceived(mensaje())
        servicio.onMessageReceived(mensaje())

        assertEquals(1, shadowOf(gestor).allNotifications.size)
    }

    @Test
    fun elIntentDelAvisoLlevaLosDatosParaAbrirElDestino() {
        val intent = IntentsNotificacion.crear(
            contexto,
            mapOf("tipo" to "ESTADO_SINIESTRO", "siniestro_id" to "SIN-1", "notificacion_id" to "N-1")
        )

        val apertura = IntentsNotificacion.apertura(intent)

        assertEquals(DestinoNotificacion.DetalleSiniestro("SIN-1"), apertura?.destino)
        assertEquals("N-1", apertura?.notificacionId)
    }

    @Test
    fun sinPermisoDeNotificacionesNoSeMuestraNada() {
        shadowOf(contexto).denyPermissions(Manifest.permission.POST_NOTIFICATIONS)

        servicio().onMessageReceived(mensaje())

        assertTrue(shadowOf(gestor).allNotifications.isEmpty())
    }

    @Test
    fun unMensajeSoloDeDatosNoMuestraNada() {
        servicio().onMessageReceived(mensaje(conAviso = false))

        assertTrue(shadowOf(gestor).allNotifications.isEmpty())
    }

    @Test
    fun unTokenNuevoSeEntregaAQuienEstaEscuchando() {
        var recibido: String? = null
        NuevoTokenPush.alRecibir = { recibido = it }

        servicio().onNewToken("tok-nuevo")

        assertEquals("tok-nuevo", recibido)
    }

    @Test
    fun unTokenNuevoSinNadieEscuchandoSeIgnora() {
        NuevoTokenPush.alRecibir = null

        servicio().onNewToken("tok-nuevo")

        assertNull(NuevoTokenPush.alRecibir)
    }
}
