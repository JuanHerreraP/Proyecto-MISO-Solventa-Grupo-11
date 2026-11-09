package com.example.solventa.domain.asesor

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.Billetera
import com.example.solventa.domain.polizas.SesionAutenticada

/** Estado que observa la UI del asesor de ventas (HU20). */
data class EstadoAsesor(
    val cargando: Boolean = false,
    val clientes: List<ClienteDeAsesor> = emptyList(),
    val error: String? = null,
    /** Asociación de un nuevo cliente en curso. */
    val asociando: Boolean = false,
    val errorAsociar: String? = null,
    /** Evento: se asoció un cliente; la UI muestra el aviso y lo consume. */
    val clienteAsociado: ClienteDeAsesor? = null,
    /** Cliente elegido para registrarle un siniestro. */
    val clienteSeleccionado: ClienteDeAsesor? = null,
    /** Pólizas vigentes del cliente seleccionado, para elegir la afectada. */
    val cargandoPolizas: Boolean = false,
    val polizasCliente: Billetera? = null,
    val errorPolizas: String? = null,
    /** Alta de un asesor por el manager en curso (SERVICIO_INTERNO). */
    val creandoAsesor: Boolean = false,
    val errorCrearAsesor: String? = null,
    /** Evento: se creó un asesor; la UI muestra la confirmación y lo consume. */
    val asesorCreado: ClienteDeAsesor? = null
)

object MensajesAsesor {
    const val SIN_CONEXION =
        "No pudimos conectarnos con Solventa. Revisa tu conexión e inténtalo de nuevo."
    const val ERROR_CLIENTES = "No pudimos cargar tus clientes. Inténtalo de nuevo en unos minutos."
    const val ERROR_POLIZAS = "No pudimos cargar las pólizas del cliente. Inténtalo de nuevo."
    const val SESION_VENCIDA = "Tu sesión expiró. Vuelve a ingresar."
    const val CLIENTE_NO_ENCONTRADO = "No existe un cliente con ese correo."
    const val CLIENTE_YA_ASOCIADO = "Ese cliente ya está asociado a tu cuenta."
    const val ASOCIAR_FALLIDO = "No pudimos asociar al cliente. Inténtalo de nuevo."
    const val EMAIL_YA_EXISTE = "Ya existe un usuario con ese correo."
    const val DOCUMENTO_YA_EXISTE = "Ya existe una cuenta con ese tipo y número de documento."
    const val KYC_RECHAZADO = "La validación de identidad no fue aprobada."
    const val CREAR_ASESOR_FALLIDO = "No pudimos crear el asesor. Inténtalo de nuevo."
    const val SIN_PERMISOS = "No tienes permisos para crear asesores."
}

/**
 * Reglas del asesor de ventas (HU20), sin dependencias de Android.
 *
 * - Lista y asocia los clientes que atiende; el backend usa la identidad del token.
 * - Al elegir un cliente carga sus pólizas vigentes para el registro asistido de siniestros.
 * - Un manager (SERVICIO_INTERNO) puede crear un asesor desde aquí.
 * - Si el backend rechaza el token (401), la sesión se cierra. Una respuesta que llega después
 *   de limpiar se ignora: pertenece a la sesión anterior.
 */
class AsesorCoordinator(
    private val gateway: AsesorGateway,
    private val sesion: SesionAutenticada
) {
    var observador: ((EstadoAsesor) -> Unit)? = null
        set(value) {
            field = value
            value?.invoke(estado)
        }

    var estado: EstadoAsesor = EstadoAsesor()
        private set(value) {
            field = value
            observador?.invoke(value)
        }

    private var generacion = 0

    suspend fun cargarClientes() {
        if (estado.cargando) return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(cargando = true, error = null)
        val inicio = generacion
        val resultado = gateway.listarClientes(token)
        if (inicio != generacion) return

        estado = when (resultado) {
            is ResultadoApi.Exito -> estado.copy(cargando = false, clientes = resultado.valor)
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) return rechazada()
                estado.copy(cargando = false, error = MensajesAsesor.ERROR_CLIENTES)
            }
            ResultadoApi.SinConexion -> estado.copy(cargando = false, error = MensajesAsesor.SIN_CONEXION)
        }
    }

    suspend fun asociarCliente(email: String) {
        if (estado.asociando) return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(asociando = true, errorAsociar = null, clienteAsociado = null)
        val inicio = generacion
        val resultado = gateway.asociarCliente(token, email.trim())
        if (inicio != generacion) return

        estado = when (resultado) {
            is ResultadoApi.Exito -> {
                val yaEstaba = estado.clientes.any { it.clienteId == resultado.valor.clienteId }
                val clientes = if (yaEstaba) estado.clientes else estado.clientes + resultado.valor
                estado.copy(
                    asociando = false,
                    clientes = clientes.sortedBy { it.nombre.lowercase() },
                    clienteAsociado = resultado.valor
                )
            }
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) return rechazada()
                estado.copy(asociando = false, errorAsociar = mensajeAsociar(resultado.codigo, resultado.http))
            }
            ResultadoApi.SinConexion -> estado.copy(asociando = false, errorAsociar = MensajesAsesor.SIN_CONEXION)
        }
    }

    /** Elige un cliente y carga sus pólizas vigentes para el registro asistido. */
    suspend fun seleccionarCliente(cliente: ClienteDeAsesor) {
        estado = estado.copy(
            clienteSeleccionado = cliente,
            polizasCliente = null,
            errorPolizas = null,
            cargandoPolizas = true
        )
        val token = tokenOFinalizar() ?: return
        val inicio = generacion
        val resultado = gateway.polizasDeCliente(token, cliente.clienteId)
        if (inicio != generacion) return

        estado = when (resultado) {
            is ResultadoApi.Exito -> estado.copy(cargandoPolizas = false, polizasCliente = resultado.valor)
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) return rechazada()
                estado.copy(cargandoPolizas = false, errorPolizas = MensajesAsesor.ERROR_POLIZAS)
            }
            ResultadoApi.SinConexion -> estado.copy(cargandoPolizas = false, errorPolizas = MensajesAsesor.SIN_CONEXION)
        }
    }

    suspend fun crearAsesor(datos: DatosNuevoAsesor) {
        if (estado.creandoAsesor) return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(creandoAsesor = true, errorCrearAsesor = null, asesorCreado = null)
        val inicio = generacion
        val resultado = gateway.crearAsesor(token, datos)
        if (inicio != generacion) return

        estado = when (resultado) {
            is ResultadoApi.Exito -> estado.copy(creandoAsesor = false, asesorCreado = resultado.valor)
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) return rechazada()
                estado.copy(creandoAsesor = false, errorCrearAsesor = mensajeCrearAsesor(resultado.codigo, resultado.http))
            }
            ResultadoApi.SinConexion -> estado.copy(creandoAsesor = false, errorCrearAsesor = MensajesAsesor.SIN_CONEXION)
        }
    }

    fun consumirClienteAsociado() {
        if (estado.clienteAsociado != null) estado = estado.copy(clienteAsociado = null)
    }

    fun consumirErrorAsociar() {
        if (estado.errorAsociar != null) estado = estado.copy(errorAsociar = null)
    }

    fun consumirAsesorCreado() {
        if (estado.asesorCreado != null) estado = estado.copy(asesorCreado = null)
    }

    fun consumirErrorCrearAsesor() {
        if (estado.errorCrearAsesor != null) estado = estado.copy(errorCrearAsesor = null)
    }

    /** Limpia la selección del cliente y sus pólizas, al salir del formulario asistido. */
    fun limpiarSeleccion() {
        estado = estado.copy(
            clienteSeleccionado = null,
            polizasCliente = null,
            errorPolizas = null,
            cargandoPolizas = false
        )
    }

    /** Se llama al cerrar o perder la sesión. */
    fun limpiar() {
        generacion++
        if (estado != EstadoAsesor()) estado = EstadoAsesor()
    }

    private fun tokenOFinalizar(): String? {
        val token = sesion.accessTokenVigente()
        if (token == null) rechazada()
        return token
    }

    private fun rechazada() {
        generacion++
        estado = EstadoAsesor(error = MensajesAsesor.SESION_VENCIDA)
        sesion.sesionRechazada()
    }

    private fun mensajeAsociar(codigo: String?, http: Int): String = when {
        codigo == "CLIENTE_NO_ENCONTRADO" || http == 404 -> MensajesAsesor.CLIENTE_NO_ENCONTRADO
        codigo == "CLIENTE_YA_ASOCIADO" || http == 409 -> MensajesAsesor.CLIENTE_YA_ASOCIADO
        else -> MensajesAsesor.ASOCIAR_FALLIDO
    }

    private fun mensajeCrearAsesor(codigo: String?, http: Int): String = when {
        codigo == "EMAIL_ALREADY_EXISTS" -> MensajesAsesor.EMAIL_YA_EXISTE
        codigo == "DOCUMENT_ALREADY_EXISTS" -> MensajesAsesor.DOCUMENTO_YA_EXISTE
        codigo == "KYC_REJECTED" -> MensajesAsesor.KYC_RECHAZADO
        http == 403 -> MensajesAsesor.SIN_PERMISOS
        else -> MensajesAsesor.CREAR_ASESOR_FALLIDO
    }
}
