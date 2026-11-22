package com.example.solventa.domain.notificaciones

import com.example.solventa.domain.auth.ResultadoApi

/** Qué evento originó la notificación (HU05). Los nombres coinciden con los del backend. */
enum class TipoNotificacion {
    PAGO_PARAMETRICO,
    VENCIMIENTO_POLIZA,
    ESTADO_SINIESTRO;

    companion object {
        fun desdeCodigo(codigo: String?): TipoNotificacion? =
            entries.firstOrNull { it.name == codigo }
    }
}

/**
 * Una notificación de la bandeja. [datos] dice a dónde lleva al tocarla (`poliza_id`,
 * `siniestro_id`…). [creadaEn] llega en ISO 8601.
 */
data class Notificacion(
    val notificacionId: String,
    val tipo: TipoNotificacion,
    val titulo: String,
    val cuerpo: String,
    val datos: Map<String, String>,
    val creadaEn: String,
    val leida: Boolean
) {
    val destino: DestinoNotificacion get() = destinoDe(tipo, datos)
}

/** La bandeja del cliente, la más reciente primero, y cuántas no ha leído. */
data class Bandeja(
    val notificaciones: List<Notificacion>,
    val noLeidas: Int
) {
    val vacia: Boolean get() = notificaciones.isEmpty()
}

/** A dónde lleva una notificación al tocarla (criterios 2 y 3 de la historia). */
sealed interface DestinoNotificacion {
    /** Un vencimiento abre el flujo de renovación de esa póliza. */
    data class Renovacion(val polizaId: String) : DestinoNotificacion

    /** Un cambio de estado o un pago paramétrico abre el detalle de ese siniestro. */
    data class DetalleSiniestro(val siniestroId: String) : DestinoNotificacion

    /** Sin destino propio (por ejemplo, un resumen agrupado): se ve la bandeja completa. */
    data object Bandeja : DestinoNotificacion
}

/**
 * El destino de un evento según su tipo y sus datos. Si falta el identificador necesario,
 * lleva a la bandeja en vez de a una pantalla que no podría mostrar nada.
 */
fun destinoDe(tipo: TipoNotificacion?, datos: Map<String, String>): DestinoNotificacion {
    val polizaId = datos[CLAVE_POLIZA_ID]?.takeIf(String::isNotBlank)
    val siniestroId = datos[CLAVE_SINIESTRO_ID]?.takeIf(String::isNotBlank)
    return when (tipo) {
        TipoNotificacion.VENCIMIENTO_POLIZA ->
            polizaId?.let(DestinoNotificacion::Renovacion) ?: DestinoNotificacion.Bandeja
        TipoNotificacion.PAGO_PARAMETRICO, TipoNotificacion.ESTADO_SINIESTRO ->
            siniestroId?.let(DestinoNotificacion::DetalleSiniestro) ?: DestinoNotificacion.Bandeja
        null -> DestinoNotificacion.Bandeja
    }
}

/** Claves de los datos que manda el backend, en la notificación y en el push de FCM. */
const val CLAVE_TIPO = "tipo"
const val CLAVE_NOTIFICACION_ID = "notificacion_id"
const val CLAVE_POLIZA_ID = "poliza_id"
const val CLAVE_SINIESTRO_ID = "siniestro_id"

/** Puerto hacia el backend de notificaciones. El backend filtra por la identidad del token. */
interface NotificacionesGateway {
    suspend fun listar(accessToken: String): ResultadoApi<Bandeja>

    suspend fun contarNoLeidas(accessToken: String): ResultadoApi<Int>

    /** Marca una como leída y devuelve cuántas quedan sin leer. */
    suspend fun marcarLeida(accessToken: String, notificacionId: String): ResultadoApi<Int>

    suspend fun registrarDispositivo(accessToken: String, tokenPush: String): ResultadoApi<Unit>

    suspend fun darDeBajaDispositivo(accessToken: String, tokenPush: String): ResultadoApi<Unit>

    suspend fun obtenerPreferencia(accessToken: String): ResultadoApi<Boolean>

    suspend fun cambiarPreferencia(accessToken: String, pushHabilitado: Boolean): ResultadoApi<Boolean>
}

/**
 * De dónde sale el token de push del teléfono. Con Firebase lo da FCM; sin Firebase no hay token y
 * la app solo usa la bandeja. Es un puerto para no atar el dominio a Firebase.
 */
interface ProveedorTokenPush {
    /** El token actual del dispositivo, o null si no hay (sin Firebase o sin conexión con Google). */
    suspend fun token(): String?

    /** Descarta el token (cierre de sesión) para que el próximo inicio pida uno nuevo. */
    suspend fun olvidar()
}

/** Mientras no haya Firebase configurado: no hay token y no se registra ningún dispositivo. */
object SinProveedorPush : ProveedorTokenPush {
    override suspend fun token(): String? = null

    override suspend fun olvidar() = Unit
}
