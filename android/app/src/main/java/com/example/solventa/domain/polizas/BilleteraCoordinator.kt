package com.example.solventa.domain.polizas

import com.example.solventa.domain.auth.ResultadoApi

/** Estado que observa la UI de la billetera y del certificado. */
data class EstadoBilletera(
    val cargando: Boolean = false,
    val billetera: Billetera? = null,
    val error: String? = null,
    val cargandoCertificado: Boolean = false,
    val certificado: Certificado? = null,
    val errorCertificado: String? = null,
    val compartiendo: Boolean = false,
    /** Evento: la UI debe abrir el menú de compartir con este enlace y luego consumirlo. */
    val enlaceParaCompartir: EnlaceCompartido? = null,
    /** Aviso pasajero, por ejemplo cuando no se pudo generar el enlace. */
    val mensaje: String? = null
)

object MensajesBilletera {
    const val SIN_CONEXION =
        "No pudimos conectarnos con Solventa. Revisa tu conexión e inténtalo de nuevo."
    const val ERROR_GENERICO = "No pudimos cargar tu billetera. Inténtalo de nuevo en unos minutos."
    const val POLIZA_NO_ENCONTRADA = "No encontramos esa póliza en tu billetera."
    const val CERTIFICADO_NO_DISPONIBLE = "No pudimos cargar el certificado. Inténtalo de nuevo."
    const val COMPARTIR_FALLIDO = "No pudimos generar el enlace para compartir. Inténtalo de nuevo."
    const val SESION_VENCIDA = "Tu sesión expiró. Vuelve a ingresar."
}

/**
 * Reglas de la HU07 (BPM-31), sin dependencias de Android.
 *
 * - Pide al backend solo las pólizas del usuario autenticado; el filtro lo hace el backend
 *   con la identidad del token, la app nunca envía un identificador de cliente.
 * - Si el backend rechaza el token (401), la sesión se cierra.
 * - Al cerrar sesión se descarta todo lo cargado, para que otro usuario no lo vea. Una
 *   respuesta que llega después de limpiar se ignora: pertenece a la sesión anterior.
 */
class BilleteraCoordinator(
    private val gateway: PolizasGateway,
    private val sesion: SesionAutenticada
) {
    var observador: ((EstadoBilletera) -> Unit)? = null
        set(value) {
            field = value
            value?.invoke(estado)
        }

    var estado: EstadoBilletera = EstadoBilletera()
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
        val resultado = gateway.billetera(token)
        if (inicio != generacion) return

        estado = when (resultado) {
            is ResultadoApi.Exito -> estado.copy(cargando = false, billetera = resultado.valor)
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) return rechazada()
                estado.copy(cargando = false, error = MensajesBilletera.ERROR_GENERICO)
            }
            ResultadoApi.SinConexion -> estado.copy(cargando = false, error = MensajesBilletera.SIN_CONEXION)
        }
    }

    suspend fun verCertificado(polizaId: String) {
        if (estado.cargandoCertificado) return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(
            cargandoCertificado = true,
            certificado = estado.certificado?.takeIf { it.polizaId == polizaId },
            errorCertificado = null
        )
        val inicio = generacion
        val resultado = gateway.certificado(token, polizaId)
        if (inicio != generacion) return

        estado = when (resultado) {
            is ResultadoApi.Exito -> estado.copy(cargandoCertificado = false, certificado = resultado.valor)
            is ResultadoApi.Fallo -> when (resultado.http) {
                401 -> return rechazada()
                403, 404 -> estado.copy(
                    cargandoCertificado = false,
                    certificado = null,
                    errorCertificado = MensajesBilletera.POLIZA_NO_ENCONTRADA
                )
                else -> estado.copy(
                    cargandoCertificado = false,
                    errorCertificado = MensajesBilletera.CERTIFICADO_NO_DISPONIBLE
                )
            }
            ResultadoApi.SinConexion -> estado.copy(
                cargandoCertificado = false,
                errorCertificado = MensajesBilletera.SIN_CONEXION
            )
        }
    }

    suspend fun compartir(polizaId: String) {
        if (estado.compartiendo) return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(compartiendo = true, mensaje = null)
        val inicio = generacion
        val resultado = gateway.compartir(token, polizaId)
        if (inicio != generacion) return

        estado = when (resultado) {
            is ResultadoApi.Exito -> estado.copy(compartiendo = false, enlaceParaCompartir = resultado.valor)
            is ResultadoApi.Fallo -> when (resultado.http) {
                401 -> return rechazada()
                403, 404 -> estado.copy(compartiendo = false, mensaje = MensajesBilletera.POLIZA_NO_ENCONTRADA)
                else -> estado.copy(compartiendo = false, mensaje = MensajesBilletera.COMPARTIR_FALLIDO)
            }
            ResultadoApi.SinConexion -> estado.copy(compartiendo = false, mensaje = MensajesBilletera.SIN_CONEXION)
        }
    }

    fun enlaceCompartido() {
        if (estado.enlaceParaCompartir != null) estado = estado.copy(enlaceParaCompartir = null)
    }

    fun consumirMensaje() {
        if (estado.mensaje != null) estado = estado.copy(mensaje = null)
    }

    fun cerrarCertificado() {
        estado = estado.copy(
            cargandoCertificado = false,
            certificado = null,
            errorCertificado = null,
            compartiendo = false,
            enlaceParaCompartir = null,
            mensaje = null
        )
    }

    /** Se llama al cerrar o perder la sesión. */
    fun limpiar() {
        generacion++
        if (estado != EstadoBilletera()) estado = EstadoBilletera()
    }

    private fun tokenOFinalizar(): String? {
        val token = sesion.accessTokenVigente()
        if (token == null) rechazada()
        return token
    }

    private fun rechazada() {
        generacion++
        estado = EstadoBilletera(mensaje = MensajesBilletera.SESION_VENCIDA)
        sesion.sesionRechazada()
    }
}
