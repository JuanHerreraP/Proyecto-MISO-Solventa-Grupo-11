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
    val errorListado: String? = null,
    val cargandoPendientes: Boolean = false,
    val pendientes: List<PrimaPendiente> = emptyList(),
    val errorPendientes: String? = null,
    val cargandoComprobante: Boolean = false,
    /** El último comprobante consultado; el de un pago aprobado se carga solo. */
    val comprobante: ComprobantePago? = null,
    /** True cuando el cliente pidió verlo (se muestra en un diálogo). */
    val comprobanteVisible: Boolean = false,
    val errorComprobante: String? = null
)

object MensajesPagos {
    const val COTIZACION_NO_VIGENTE = "La cotización ya no está vigente. Crea una nueva para continuar."
    const val COTIZACION_YA_PAGADA = "Esta cotización ya tiene un pago aprobado."
    const val DATOS_INVALIDOS = "Revisa los datos del medio de pago e inténtalo de nuevo."
    const val SIN_CONEXION = "No pudimos conectarnos con Solventa. Revisa tu conexión e inténtalo de nuevo."
    const val ERROR_GENERICO = "No pudimos procesar el pago. Inténtalo de nuevo."
    const val SESION_VENCIDA = "Tu sesión expiró. Vuelve a ingresar."
    const val PENDIENTES_NO_DISPONIBLES =
        "No pudimos consultar tus pagos pendientes. Inténtalo de nuevo."
    const val COMPROBANTE_NO_DISPONIBLE = "No pudimos consultar el comprobante. Inténtalo de nuevo."
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

    suspend fun pendientes(accessToken: String): ResultadoApi<List<PrimaPendiente>>

    suspend fun comprobante(accessToken: String, pagoId: String): ResultadoApi<ComprobantePago>
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
        cargarComprobanteDelPagoAprobado(inicio)
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
        cargarComprobanteDelPagoAprobado(inicio)
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

    /** Prima pendiente de pago: renovaciones, cotizaciones sin pagar y contratos por firmar. */
    suspend fun cargarPendientes() {
        if (estado.cargandoPendientes) return
        val token = sesion.accessTokenVigente() ?: return rechazada()
        estado = estado.copy(cargandoPendientes = true, errorPendientes = null)
        val inicio = generacion
        val respuesta = gateway.pendientes(token)
        if (inicio != generacion) return

        estado = when (respuesta) {
            is ResultadoApi.Exito -> estado.copy(
                cargandoPendientes = false,
                pendientes = respuesta.valor,
                errorPendientes = null
            )
            is ResultadoApi.Fallo -> when (respuesta.http) {
                401 -> return rechazada()
                else -> estado.copy(
                    cargandoPendientes = false,
                    errorPendientes = MensajesPagos.PENDIENTES_NO_DISPONIBLES
                )
            }
            ResultadoApi.SinConexion -> estado.copy(
                cargandoPendientes = false,
                errorPendientes = MensajesPagos.SIN_CONEXION
            )
        }
    }

    /** El cliente pide ver el comprobante de un pago aprobado. */
    suspend fun verComprobante(pagoId: String) {
        if (estado.cargandoComprobante) return
        val token = sesion.accessTokenVigente() ?: return rechazada()
        estado = estado.copy(
            cargandoComprobante = true,
            comprobanteVisible = true,
            comprobante = estado.comprobante?.takeIf { it.pagoId == pagoId },
            errorComprobante = null
        )
        val inicio = generacion
        val respuesta = gateway.comprobante(token, pagoId)
        if (inicio != generacion) return

        estado = when (respuesta) {
            is ResultadoApi.Exito -> estado.copy(cargandoComprobante = false, comprobante = respuesta.valor)
            is ResultadoApi.Fallo -> when (respuesta.http) {
                401 -> return rechazada()
                else -> estado.copy(
                    cargandoComprobante = false,
                    errorComprobante = MensajesPagos.COMPROBANTE_NO_DISPONIBLE
                )
            }
            ResultadoApi.SinConexion -> estado.copy(
                cargandoComprobante = false,
                errorComprobante = MensajesPagos.SIN_CONEXION
            )
        }
    }

    fun cerrarComprobante() {
        estado = estado.copy(comprobanteVisible = false, errorComprobante = null)
    }

    /**
     * Con el pago aprobado se trae su comprobante para mostrarlo en la confirmación. Es un extra:
     * si no se puede consultar, la confirmación sigue siendo válida y no se muestra error.
     */
    private suspend fun cargarComprobanteDelPagoAprobado(generacionInicial: Int) {
        val pago = estado.pago?.takeIf { it.estado == EstadoPago.APROBADO } ?: return
        val token = sesion.accessTokenVigente() ?: return
        val respuesta = gateway.comprobante(token, pago.pagoId)
        if (generacionInicial != generacion) return
        if (respuesta is ResultadoApi.Exito) {
            estado = estado.copy(comprobante = respuesta.valor)
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
