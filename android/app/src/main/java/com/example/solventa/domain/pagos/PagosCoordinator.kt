package com.example.solventa.domain.pagos

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.SesionAutenticada
import java.util.UUID

data class EstadoPagos(
    val procesando: Boolean = false,
    val pago: Pago? = null,
    val error: String? = null,
    val cargandoListado: Boolean = false,
    val listado: List<Pago> = emptyList(),
    val errorListado: String? = null
)

object MensajesPagos {
    const val COTIZACION_NO_VIGENTE = "La cotización ya no está vigente. Crea una nueva para continuar."
    const val COTIZACION_YA_PAGADA = "Esta cotización ya tiene un pago aprobado."
    const val DATOS_INVALIDOS = "Revisa los datos del medio de pago e inténtalo de nuevo."
    const val SIN_CONEXION = "No pudimos conectarnos con Solventa. Revisa tu conexión e inténtalo de nuevo."
    const val ERROR_GENERICO = "No pudimos procesar el pago. Inténtalo de nuevo."
    const val SESION_VENCIDA = "Tu sesión expiró. Vuelve a ingresar."
}

/** Puerto hacia el backend de recaudo (HU13). */
interface PagosGateway {
    suspend fun pagar(
        accessToken: String,
        idempotencyKey: String,
        solicitud: SolicitudPago
    ): ResultadoApi<Pago>

    suspend fun consultar(accessToken: String, pagoId: String): ResultadoApi<Pago>

    suspend fun listar(accessToken: String): ResultadoApi<List<Pago>>
}

/**
 * Orquesta el recaudo de la prima (HU13 / HU23) sin dependencias de Android.
 *
 * - Cada intento usa una Idempotency-Key única (UUID). Un reintento tras un rechazo
 *   genera una llave nueva para no chocar con el pago anterior; así no se duplica el cobro.
 * - 401 cierra la sesión en memoria. Una respuesta de otra generación se ignora.
 */
class PagosCoordinator(
    private val gateway: PagosGateway,
    private val sesion: SesionAutenticada,
    private val generarLlave: () -> String = { UUID.randomUUID().toString() }
) {
    var observador: ((EstadoPagos) -> Unit)? = null
        set(value) {
            field = value
            value?.invoke(estado)
        }

    var estado: EstadoPagos = EstadoPagos()
        private set(value) {
            field = value
            observador?.invoke(value)
        }

    private var generacion = 0
    private var llaveActual: String? = null

    suspend fun pagar(solicitud: SolicitudPago) {
        if (estado.procesando) return
        val token = sesion.accessTokenVigente() ?: return rechazada()
        val llave = llaveActual ?: generarLlave().also { llaveActual = it }

        estado = estado.copy(procesando = true, error = null)
        val inicio = generacion
        val respuesta = gateway.pagar(token, llave, solicitud)
        if (inicio != generacion) return

        estado = when (respuesta) {
            is ResultadoApi.Exito -> estado.copy(procesando = false, pago = respuesta.valor, error = null)
            is ResultadoApi.Fallo -> when (respuesta.http) {
                401 -> return rechazada()
                409 -> estado.copy(procesando = false, error = mensajeConflicto(respuesta.codigo))
                422 -> estado.copy(procesando = false, error = MensajesPagos.DATOS_INVALIDOS)
                else -> estado.copy(procesando = false, error = MensajesPagos.ERROR_GENERICO)
            }
            ResultadoApi.SinConexion -> estado.copy(procesando = false, error = MensajesPagos.SIN_CONEXION)
        }
    }

    suspend fun consultar(pagoId: String) {
        if (estado.procesando) return
        val token = sesion.accessTokenVigente() ?: return rechazada()
        estado = estado.copy(procesando = true, error = null)
        val inicio = generacion
        val respuesta = gateway.consultar(token, pagoId)
        if (inicio != generacion) return

        estado = when (respuesta) {
            is ResultadoApi.Exito -> estado.copy(procesando = false, pago = respuesta.valor, error = null)
            is ResultadoApi.Fallo -> when (respuesta.http) {
                401 -> return rechazada()
                else -> estado.copy(procesando = false, error = MensajesPagos.ERROR_GENERICO)
            }
            ResultadoApi.SinConexion -> estado.copy(procesando = false, error = MensajesPagos.SIN_CONEXION)
        }
    }

    /** Prepara un nuevo intento tras un rechazo: llave nueva y estado limpio. */
    fun prepararReintento() {
        llaveActual = null
        estado = estado.copy(pago = null, error = null)
    }

    suspend fun listar() {
        if (estado.cargandoListado) return
        val token = sesion.accessTokenVigente() ?: return rechazada()
        estado = estado.copy(cargandoListado = true, errorListado = null)
        val inicio = generacion
        val respuesta = gateway.listar(token)
        if (inicio != generacion) return

        estado = when (respuesta) {
            is ResultadoApi.Exito -> estado.copy(
                cargandoListado = false,
                listado = respuesta.valor,
                errorListado = null
            )
            is ResultadoApi.Fallo -> when (respuesta.http) {
                401 -> return rechazada()
                else -> estado.copy(cargandoListado = false, errorListado = MensajesPagos.ERROR_GENERICO)
            }
            ResultadoApi.SinConexion -> estado.copy(
                cargandoListado = false,
                errorListado = MensajesPagos.SIN_CONEXION
            )
        }
    }

    fun limpiar() {
        generacion++
        llaveActual = null
        if (estado != EstadoPagos()) estado = EstadoPagos()
    }

    private fun mensajeConflicto(codigo: String?): String = when (codigo) {
        "COTIZACION_NO_VIGENTE" -> MensajesPagos.COTIZACION_NO_VIGENTE
        "COTIZACION_YA_PAGADA" -> MensajesPagos.COTIZACION_YA_PAGADA
        else -> MensajesPagos.ERROR_GENERICO
    }

    private fun rechazada() {
        generacion++
        llaveActual = null
        estado = EstadoPagos(error = MensajesPagos.SESION_VENCIDA)
        sesion.sesionRechazada()
    }
}
