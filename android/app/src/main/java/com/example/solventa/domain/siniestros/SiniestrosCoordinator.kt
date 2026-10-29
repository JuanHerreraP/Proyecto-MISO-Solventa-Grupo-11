package com.example.solventa.domain.siniestros

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.SesionAutenticada

/** Estado que observa la UI de siniestros. */
data class EstadoSiniestros(
    val cargando: Boolean = false,
    val siniestros: Siniestros? = null,
    val error: String? = null,
    /** Aviso pasajero, por ejemplo cuando la sesión expira. */
    val mensaje: String? = null,
    /** Registro manual en curso. */
    val registrando: Boolean = false,
    /** Error del formulario de registro (se muestra en la pantalla de registro). */
    val errorFormulario: String? = null,
    /** Evento: el registro manual terminó bien; la UI debe volver a la lista y consumirlo. */
    val registroExitoso: Boolean = false
)

object MensajesSiniestros {
    const val SIN_CONEXION =
        "No pudimos conectarnos con Solventa. Revisa tu conexión e inténtalo de nuevo."
    const val ERROR_GENERICO =
        "No pudimos cargar tus siniestros. Inténtalo de nuevo en unos minutos."
    const val SESION_VENCIDA = "Tu sesión expiró. Vuelve a ingresar."
    const val REGISTRO_FALLIDO = "No pudimos registrar el siniestro. Inténtalo de nuevo."
    const val POLIZA_NO_ENCONTRADA = "No encontramos esa póliza en tu billetera."
    const val POLIZA_AJENA = "No tienes acceso a esta póliza."
    const val POLIZA_NO_VIGENTE = "La póliza no está vigente."
    const val DATOS_INVALIDOS = "Revisa los datos del siniestro e inténtalo de nuevo."
}

/**
 * Reglas de los siniestros del cliente (HU20), sin dependencias de Android.
 *
 * - Pide al backend solo los siniestros del usuario autenticado; el filtro lo hace el backend
 *   con la identidad del token, la app nunca envía un identificador de cliente.
 * - Si el backend rechaza el token (401), la sesión se cierra.
 * - Al cerrar sesión se descarta todo lo cargado. Una respuesta que llega después de limpiar se
 *   ignora: pertenece a la sesión anterior.
 */
class SiniestrosCoordinator(
    private val gateway: SiniestrosGateway,
    private val sesion: SesionAutenticada
) {
    var observador: ((EstadoSiniestros) -> Unit)? = null
        set(value) {
            field = value
            value?.invoke(estado)
        }

    var estado: EstadoSiniestros = EstadoSiniestros()
        private set(value) {
            field = value
            observador?.invoke(value)
        }

    /** Cambia al limpiar; una respuesta de otra generación ya no se aplica. */
    private var generacion = 0

    suspend fun cargar() {
        if (estado.cargando) return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(cargando = true, error = null)
        val inicio = generacion
        val resultado = gateway.listar(token)
        if (inicio != generacion) return

        estado = when (resultado) {
            is ResultadoApi.Exito -> estado.copy(cargando = false, siniestros = resultado.valor)
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) return rechazada()
                estado.copy(cargando = false, error = MensajesSiniestros.ERROR_GENERICO)
            }
            ResultadoApi.SinConexion ->
                estado.copy(cargando = false, error = MensajesSiniestros.SIN_CONEXION)
        }
    }

    fun consumirMensaje() {
        if (estado.mensaje != null) estado = estado.copy(mensaje = null)
    }

    /**
     * Registra manualmente un siniestro (HU20). Si el backend lo acepta, recarga la lista para
     * que el nuevo siniestro aparezca y marca [registroExitoso] para que la UI vuelva a la lista.
     */
    suspend fun registrar(solicitud: SolicitudSiniestro) {
        if (estado.registrando) return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(registrando = true, errorFormulario = null, registroExitoso = false)
        val inicio = generacion
        val resultado = gateway.registrar(token, solicitud)
        if (inicio != generacion) return

        when (resultado) {
            is ResultadoApi.Exito -> {
                estado = estado.copy(registrando = false, errorFormulario = null, registroExitoso = true)
                // El backend es la fuente de verdad: se recarga la lista con el nuevo siniestro.
                cargar()
            }
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) return rechazada()
                estado = estado.copy(
                    registrando = false,
                    errorFormulario = mensajeRegistro(resultado.http)
                )
            }
            ResultadoApi.SinConexion ->
                estado = estado.copy(registrando = false, errorFormulario = MensajesSiniestros.SIN_CONEXION)
        }
    }

    fun consumirRegistroExitoso() {
        if (estado.registroExitoso) estado = estado.copy(registroExitoso = false)
    }

    fun consumirErrorFormulario() {
        if (estado.errorFormulario != null) estado = estado.copy(errorFormulario = null)
    }

    /** Se llama al cerrar o perder la sesión. */
    fun limpiar() {
        generacion++
        if (estado != EstadoSiniestros()) estado = EstadoSiniestros()
    }

    private fun tokenOFinalizar(): String? {
        val token = sesion.accessTokenVigente()
        if (token == null) rechazada()
        return token
    }

    private fun rechazada() {
        generacion++
        estado = EstadoSiniestros(mensaje = MensajesSiniestros.SESION_VENCIDA)
        sesion.sesionRechazada()
    }

    private fun mensajeRegistro(http: Int): String = when (http) {
        404 -> MensajesSiniestros.POLIZA_NO_ENCONTRADA
        403 -> MensajesSiniestros.POLIZA_AJENA
        409 -> MensajesSiniestros.POLIZA_NO_VIGENTE
        422 -> MensajesSiniestros.DATOS_INVALIDOS
        else -> MensajesSiniestros.REGISTRO_FALLIDO
    }
}
