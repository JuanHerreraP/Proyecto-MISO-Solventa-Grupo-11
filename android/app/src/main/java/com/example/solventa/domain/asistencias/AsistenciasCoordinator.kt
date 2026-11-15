package com.example.solventa.domain.asistencias

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.SesionAutenticada
import com.example.solventa.domain.siniestros.Ubicacion

/**
 * Reglas del flujo de asistencia en sitio (HU06), sin dependencias de Android.
 *
 * El coordinador no toca el GPS ni los permisos: recibe la [Ubicacion] ya resuelta por la capa
 * de UI (que la obtiene de un proveedor testeable). Así las reglas se prueban sin emulador.
 *
 * - El backend valida siempre la póliza (existe, es del cliente, vigente, ramo con asistencia)
 *   y el prestador (existe, activo, ofrece el servicio). La app nunca envía el cliente_id.
 * - Si el backend rechaza el token (401), la sesión se cierra.
 * - Al limpiar se descarta todo lo cargado; una respuesta que llega después se ignora.
 */
class AsistenciasCoordinator(
    private val gateway: AsistenciasGateway,
    private val sesion: SesionAutenticada
) {
    var observador: ((EstadoAsistencias) -> Unit)? = null
        set(value) {
            field = value
            value?.invoke(estado)
        }

    var estado: EstadoAsistencias = EstadoAsistencias()
        private set(value) {
            field = value
            observador?.invoke(value)
        }

    private var generacion = 0

    /** Empieza el flujo con la póliza elegida y carga sus servicios de asistencia. */
    suspend fun seleccionarPoliza(polizaId: String, etiqueta: String) {
        val token = tokenOFinalizar() ?: return
        estado = EstadoAsistencias(
            paso = PasoAsistencia.SELECCION_SERVICIO,
            cargando = true,
            polizaSeleccionadaId = polizaId,
            polizaSeleccionadaEtiqueta = etiqueta
        )
        val inicio = generacion
        val resultado = gateway.servicios(token, polizaId)
        if (inicio != generacion) return
        estado = when (resultado) {
            is ResultadoApi.Exito -> estado.copy(cargando = false, servicios = resultado.valor.servicios)
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) return rechazada()
                estado.copy(cargando = false, error = mensajePoliza(resultado))
            }
            ResultadoApi.SinConexion ->
                estado.copy(cargando = false, error = MensajesAsistencias.SIN_CONEXION)
        }
    }

    fun seleccionarServicio(servicio: ServicioAsistencia) {
        estado = estado.copy(
            servicioSeleccionado = servicio,
            paso = PasoAsistencia.PERMISO_UBICACION,
            error = null
        )
    }

    /** El permiso fue denegado: no se cierra la app, se ofrece reintentar (HU06). */
    fun permisoDenegado() {
        estado = estado.copy(permisoDenegado = true, aviso = MensajesAsistencias.SIN_UBICACION)
    }

    fun consumirAviso() {
        if (estado.aviso != null) estado = estado.copy(aviso = null)
    }

    fun consumirError() {
        if (estado.error != null) estado = estado.copy(error = null)
    }

    /**
     * Con la ubicación ya obtenida por la UI, busca prestadores compatibles cercanos.
     * Sin ubicación informa y vuelve a pedir el permiso; nunca envía coordenadas ficticias.
     */
    suspend fun buscarPrestadores(ubicacion: Ubicacion?, radioKm: Double = estado.radioKm) {
        val servicio = estado.servicioSeleccionado ?: return
        val polizaId = estado.polizaSeleccionadaId ?: return
        if (ubicacion == null) {
            estado = estado.copy(
                permisoDenegado = true,
                error = MensajesAsistencias.UBICACION_NO_DISPONIBLE
            )
            return
        }
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(
            cargando = true,
            error = null,
            permisoDenegado = false,
            ubicacion = ubicacion,
            radioKm = radioKm,
            paso = PasoAsistencia.PRESTADORES
        )
        val inicio = generacion
        val resultado = gateway.prestadoresCercanos(
            token, polizaId, servicio.codigo, ubicacion.latitud, ubicacion.longitud, radioKm
        )
        if (inicio != generacion) return
        estado = when (resultado) {
            is ResultadoApi.Exito ->
                estado.copy(cargando = false, prestadores = resultado.valor.prestadores)
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) return rechazada()
                estado.copy(cargando = false, error = mensajePoliza(resultado))
            }
            ResultadoApi.SinConexion ->
                estado.copy(cargando = false, error = MensajesAsistencias.SIN_CONEXION)
        }
    }

    fun seleccionarPrestador(prestador: PrestadorCercano) {
        estado = estado.copy(
            prestadorSeleccionado = prestador,
            paso = PasoAsistencia.CONFIRMACION,
            error = null
        )
    }

    fun volverAPrestadores() {
        estado = estado.copy(paso = PasoAsistencia.PRESTADORES, error = null)
    }

    /** Solicita la asistencia. Deshabilita el botón ([solicitando]) para no duplicar el POST. */
    suspend fun solicitar(observaciones: String?) {
        if (estado.solicitando) return
        val servicio = estado.servicioSeleccionado ?: return
        val prestador = estado.prestadorSeleccionado ?: return
        val polizaId = estado.polizaSeleccionadaId ?: return
        val ubicacion = estado.ubicacion ?: return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(solicitando = true, error = null)
        val inicio = generacion
        val resultado = gateway.solicitar(
            token,
            NuevaAsistencia(
                polizaId = polizaId,
                prestadorId = prestador.prestadorId,
                servicio = servicio.codigo,
                latitud = ubicacion.latitud,
                longitud = ubicacion.longitud,
                observaciones = observaciones?.trim()?.ifBlank { null }
            )
        )
        if (inicio != generacion) return
        estado = when (resultado) {
            is ResultadoApi.Exito ->
                estado.copy(
                    solicitando = false,
                    asistenciaCreada = resultado.valor,
                    paso = PasoAsistencia.EXITO
                )
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) return rechazada()
                estado.copy(solicitando = false, error = mensajeSolicitud(resultado))
            }
            ResultadoApi.SinConexion ->
                estado.copy(solicitando = false, error = MensajesAsistencias.SIN_CONEXION)
        }
    }

    /** Lista las asistencias del cliente (pantalla "Mis asistencias"). */
    suspend fun cargarAsistencias() {
        if (estado.cargandoAsistencias) return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(
            cargandoAsistencias = true,
            error = null,
            paso = PasoAsistencia.MIS_ASISTENCIAS
        )
        val inicio = generacion
        val resultado = gateway.listar(token)
        if (inicio != generacion) return
        estado = when (resultado) {
            is ResultadoApi.Exito ->
                estado.copy(cargandoAsistencias = false, asistencias = resultado.valor)
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) return rechazada()
                estado.copy(cargandoAsistencias = false, error = MensajesAsistencias.ERROR_GENERICO)
            }
            ResultadoApi.SinConexion ->
                estado.copy(cargandoAsistencias = false, error = MensajesAsistencias.SIN_CONEXION)
        }
    }

    /** Cancela una asistencia SOLICITADA y refleja el nuevo estado en la lista. */
    suspend fun cancelar(asistenciaId: String) {
        if (estado.cancelandoId != null) return
        val token = tokenOFinalizar() ?: return
        estado = estado.copy(cancelandoId = asistenciaId, error = null)
        val inicio = generacion
        val resultado = gateway.cancelar(token, asistenciaId)
        if (inicio != generacion) return
        estado = when (resultado) {
            is ResultadoApi.Exito -> {
                val cancelada = resultado.valor
                estado.copy(
                    cancelandoId = null,
                    asistencias = estado.asistencias.map {
                        if (it.asistenciaId == cancelada.asistenciaId) cancelada else it
                    },
                    asistenciaCreada = estado.asistenciaCreada?.let {
                        if (it.asistenciaId == cancelada.asistenciaId) cancelada else it
                    }
                )
            }
            is ResultadoApi.Fallo -> {
                if (resultado.http == 401) return rechazada()
                estado.copy(cancelandoId = null, error = mensajeCancelacion(resultado))
            }
            ResultadoApi.SinConexion ->
                estado.copy(cancelandoId = null, error = MensajesAsistencias.SIN_CONEXION)
        }
    }

    /** Vuelve al inicio del flujo para una nueva solicitud, conservando la sesión. */
    fun reiniciarFlujo() {
        estado = EstadoAsistencias()
    }

    fun irAMisAsistencias() {
        estado = estado.copy(paso = PasoAsistencia.MIS_ASISTENCIAS, error = null)
    }

    /** Se llama al cerrar o perder la sesión. */
    fun limpiar() {
        generacion++
        if (estado != EstadoAsistencias()) estado = EstadoAsistencias()
    }

    private fun tokenOFinalizar(): String? {
        val token = sesion.accessTokenVigente()
        if (token == null) rechazada()
        return token
    }

    private fun rechazada() {
        generacion++
        estado = EstadoAsistencias(aviso = MensajesAsistencias.SESION_VENCIDA)
        sesion.sesionRechazada()
    }

    private fun mensajePoliza(fallo: ResultadoApi.Fallo): String = when (fallo.codigo) {
        "POLIZA_NO_ENCONTRADA" -> MensajesAsistencias.POLIZA_NO_ENCONTRADA
        "POLIZA_NO_AUTORIZADA" -> MensajesAsistencias.POLIZA_NO_AUTORIZADA
        "POLIZA_NO_VIGENTE" -> MensajesAsistencias.POLIZA_NO_VIGENTE
        "SERVICIO_NO_DISPONIBLE" -> MensajesAsistencias.SERVICIO_NO_DISPONIBLE
        else -> when (fallo.http) {
            404 -> MensajesAsistencias.POLIZA_NO_ENCONTRADA
            403 -> MensajesAsistencias.POLIZA_NO_AUTORIZADA
            409 -> MensajesAsistencias.POLIZA_NO_VIGENTE
            422 -> MensajesAsistencias.DATOS_INVALIDOS
            else -> MensajesAsistencias.ERROR_GENERICO
        }
    }

    private fun mensajeSolicitud(fallo: ResultadoApi.Fallo): String = when (fallo.codigo) {
        "PRESTADOR_NO_ENCONTRADO" -> MensajesAsistencias.PRESTADOR_NO_ENCONTRADO
        "PRESTADOR_NO_DISPONIBLE" -> MensajesAsistencias.PRESTADOR_NO_DISPONIBLE
        "SERVICIO_NO_OFRECIDO_POR_PRESTADOR" -> MensajesAsistencias.SERVICIO_NO_OFRECIDO
        "POLIZA_NO_ENCONTRADA", "POLIZA_NO_AUTORIZADA", "POLIZA_NO_VIGENTE",
        "SERVICIO_NO_DISPONIBLE" -> mensajePoliza(fallo)
        else -> MensajesAsistencias.SOLICITUD_FALLIDA
    }

    private fun mensajeCancelacion(fallo: ResultadoApi.Fallo): String = when (fallo.codigo) {
        "ASISTENCIA_NO_ENCONTRADA" -> MensajesAsistencias.ASISTENCIA_NO_ENCONTRADA
        "ASISTENCIA_YA_CANCELADA" -> MensajesAsistencias.ASISTENCIA_YA_CANCELADA
        else -> MensajesAsistencias.CANCELACION_FALLIDA
    }
}
