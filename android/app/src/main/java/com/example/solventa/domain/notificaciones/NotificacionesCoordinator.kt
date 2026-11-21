package com.example.solventa.domain.notificaciones

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.SesionAutenticada

data class EstadoNotificaciones(
    val cargando: Boolean = false,
    val bandeja: Bandeja? = null,
    val error: String? = null,
    /** Para la insignia de la campana: se mantiene aunque la bandeja no esté cargada. */
    val noLeidas: Int = 0,
    /** Null mientras no se ha consultado. Sin preferencia guardada el backend responde true. */
    val pushHabilitado: Boolean? = null,
    val cambiandoPreferencia: Boolean = false,
    val errorPreferencia: String? = null
)

object MensajesNotificaciones {
    const val SIN_CONEXION =
        "No pudimos conectarnos con Solventa. Revisa tu conexión e inténtalo de nuevo."
    const val ERROR_GENERICO =
        "No pudimos cargar tus notificaciones. Inténtalo de nuevo en unos minutos."
    const val PREFERENCIA_NO_GUARDADA =
        "No pudimos guardar tu preferencia. Inténtalo de nuevo."
    const val SESION_VENCIDA = "Tu sesión expiró. Vuelve a ingresar."
}

/**
 * Notificaciones del cliente (HU05), sin dependencias de Android.
 *
 * - La bandeja y la insignia salen siempre del backend, que registra los eventos aunque el
 *   push esté deshabilitado.
 * - El token de push del teléfono se registra al iniciar sesión y se da de baja al cerrarla. Sin
 *   Firebase no hay token ([SinProveedorPush]) y la app solo usa la bandeja.
 * - 401 cierra la sesión en memoria. Una respuesta de otra generación se ignora.
 */
class NotificacionesCoordinator(
    private val gateway: NotificacionesGateway,
    private val sesion: SesionAutenticada,
    private val proveedorToken: ProveedorTokenPush = SinProveedorPush
) {
    var observador: ((EstadoNotificaciones) -> Unit)? = null
        set(value) {
            field = value
            value?.invoke(estado)
        }

    var estado: EstadoNotificaciones = EstadoNotificaciones()
        private set(value) {
            field = value
            observador?.invoke(value)
        }

    private var generacion = 0

    /** El token que este teléfono tiene registrado en el backend, para poder darlo de baja. */
    private var tokenRegistrado: String? = null

    suspend fun cargar() {
        if (estado.cargando) return
        val token = sesion.accessTokenVigente() ?: return rechazada()
        estado = estado.copy(cargando = true, error = null)
        val inicio = generacion
        val respuesta = gateway.listar(token)
        if (inicio != generacion) return

        estado = when (respuesta) {
            is ResultadoApi.Exito -> estado.copy(
                cargando = false,
                bandeja = respuesta.valor,
                noLeidas = respuesta.valor.noLeidas,
                error = null
            )
            is ResultadoApi.Fallo -> when (respuesta.http) {
                401 -> return rechazada()
                else -> estado.copy(cargando = false, error = MensajesNotificaciones.ERROR_GENERICO)
            }
            ResultadoApi.SinConexion -> estado.copy(
                cargando = false,
                error = MensajesNotificaciones.SIN_CONEXION
            )
        }
    }

    /** Refresca solo el número de la insignia; un fallo no molesta al cliente. */
    suspend fun actualizarInsignia() {
        val token = sesion.accessTokenVigente() ?: return
        val inicio = generacion
        val respuesta = gateway.contarNoLeidas(token)
        if (inicio != generacion) return
        when (respuesta) {
            is ResultadoApi.Exito -> estado = estado.copy(noLeidas = respuesta.valor)
            is ResultadoApi.Fallo -> if (respuesta.http == 401) rechazada()
            ResultadoApi.SinConexion -> Unit
        }
    }

    /** Marca una como leída; repetirlo no cambia nada. Un fallo deja la notificación como estaba. */
    suspend fun marcarLeida(notificacionId: String) {
        val token = sesion.accessTokenVigente() ?: return
        val inicio = generacion
        val respuesta = gateway.marcarLeida(token, notificacionId)
        if (inicio != generacion) return
        when (respuesta) {
            is ResultadoApi.Exito -> estado = estado.copy(
                noLeidas = respuesta.valor,
                bandeja = estado.bandeja?.let { bandeja ->
                    bandeja.copy(
                        notificaciones = bandeja.notificaciones.map {
                            if (it.notificacionId == notificacionId) it.copy(leida = true) else it
                        },
                        noLeidas = respuesta.valor
                    )
                }
            )
            is ResultadoApi.Fallo -> if (respuesta.http == 401) rechazada()
            ResultadoApi.SinConexion -> Unit
        }
    }

    // --- Preferencia de push --------------------------------------------------------------

    suspend fun cargarPreferencia() {
        val token = sesion.accessTokenVigente() ?: return rechazada()
        val inicio = generacion
        val respuesta = gateway.obtenerPreferencia(token)
        if (inicio != generacion) return
        when (respuesta) {
            is ResultadoApi.Exito -> estado = estado.copy(pushHabilitado = respuesta.valor)
            is ResultadoApi.Fallo -> if (respuesta.http == 401) rechazada()
            ResultadoApi.SinConexion -> Unit
        }
    }

    /**
     * Habilita o deshabilita el push. Si no se pudo guardar, el interruptor vuelve a como estaba
     * y se informa. Con el push apagado los eventos siguen apareciendo en la bandeja.
     */
    suspend fun cambiarPreferencia(pushHabilitado: Boolean) {
        if (estado.cambiandoPreferencia) return
        val token = sesion.accessTokenVigente() ?: return rechazada()
        val anterior = estado.pushHabilitado
        estado = estado.copy(
            cambiandoPreferencia = true,
            pushHabilitado = pushHabilitado,
            errorPreferencia = null
        )
        val inicio = generacion
        val respuesta = gateway.cambiarPreferencia(token, pushHabilitado)
        if (inicio != generacion) return

        estado = when (respuesta) {
            is ResultadoApi.Exito -> estado.copy(
                cambiandoPreferencia = false,
                pushHabilitado = respuesta.valor
            )
            is ResultadoApi.Fallo -> if (respuesta.http == 401) {
                return rechazada()
            } else {
                estado.copy(
                    cambiandoPreferencia = false,
                    pushHabilitado = anterior,
                    errorPreferencia = MensajesNotificaciones.PREFERENCIA_NO_GUARDADA
                )
            }
            ResultadoApi.SinConexion -> estado.copy(
                cambiandoPreferencia = false,
                pushHabilitado = anterior,
                errorPreferencia = MensajesNotificaciones.SIN_CONEXION
            )
        }
    }

    // --- Dispositivo ----------------------------------------------------------------------

    /**
     * Registra el token de push de este teléfono para la sesión actual. Se llama al iniciar sesión.
     * Devuelve false si no hay token (sin Firebase) o no se pudo registrar: no es un error para el
     * cliente, la bandeja funciona igual.
     */
    suspend fun registrarDispositivo(): Boolean {
        val tokenPush = proveedorToken.token() ?: return false
        return registrarToken(tokenPush)
    }

    /** Registra un token concreto: lo usa el servicio de mensajería cuando FCM entrega uno nuevo. */
    suspend fun registrarToken(tokenPush: String): Boolean {
        val token = sesion.accessTokenVigente() ?: return false
        val inicio = generacion
        val respuesta = gateway.registrarDispositivo(token, tokenPush)
        if (inicio != generacion) return false
        return when (respuesta) {
            is ResultadoApi.Exito -> {
                tokenRegistrado = tokenPush
                true
            }
            is ResultadoApi.Fallo -> {
                if (respuesta.http == 401) rechazada()
                false
            }
            ResultadoApi.SinConexion -> false
        }
    }

    /**
     * Da de baja el token de este teléfono (cierre de sesión), mientras la sesión aún es válida, y
     * descarta el token local. Es de mejor esfuerzo: si no se logra, el cierre de sesión sigue.
     */
    suspend fun darDeBajaDispositivo() {
        val tokenPush = tokenRegistrado ?: proveedorToken.token()
        val token = sesion.accessTokenVigente()
        if (tokenPush != null && token != null) {
            gateway.darDeBajaDispositivo(token, tokenPush)
        }
        tokenRegistrado = null
        proveedorToken.olvidar()
    }

    /** Descarta lo cargado en memoria (cierre de sesión o cambio de usuario). */
    fun limpiar() {
        generacion++
        tokenRegistrado = null
        if (estado != EstadoNotificaciones()) estado = EstadoNotificaciones()
    }

    private fun rechazada() {
        generacion++
        tokenRegistrado = null
        estado = EstadoNotificaciones(error = MensajesNotificaciones.SESION_VENCIDA)
        sesion.sesionRechazada()
    }
}
