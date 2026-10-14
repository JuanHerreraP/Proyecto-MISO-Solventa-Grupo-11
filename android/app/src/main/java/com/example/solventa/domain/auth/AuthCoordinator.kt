package com.example.solventa.domain.auth

import com.example.solventa.biometric.FalloBiometrico

/**
 * Reglas de la HU02 (BPM-23), sin dependencias de Android para poder probarlas en la JVM.
 *
 * - El access token y el refresh token viven solo en memoria.
 * - El refresh token se guarda cifrado en la [BovedaSesion] cuando el usuario activa la huella.
 * - Ingreso biométrico: la huella abre la bóveda, el refresh token se cambia por uno nuevo
 *   (rotación en el backend) y el nuevo se vuelve a guardar.
 * - Si la biometría falla, se bloquea o cambia, se ofrece el ingreso con credenciales.
 */
class AuthCoordinator(
    private val gateway: AuthGateway,
    private val boveda: BovedaSesion,
    private val reloj: Reloj,
    private val biometriaDisponible: () -> Boolean
) {
    var observador: ((EstadoAuth) -> Unit)? = null
        set(value) {
            field = value
            value?.invoke(estado)
        }

    var estado: EstadoAuth = EstadoAuth(biometriaActivada = boveda.tieneSesionGuardada())
        private set(value) {
            field = value
            observador?.invoke(value)
        }

    private var tokens: Tokens? = null

    suspend fun registrar(datos: DatosRegistro) {
        if (estado.cargando) return
        estado = estado.copy(cargando = true, mensaje = null, registroCompletado = false)

        when (val resultado = gateway.registrar(datos)) {
            is ResultadoApi.Exito -> {
                if (resultado.valor.kycValidado) {
                    estado = estado.copy(
                        cargando = false,
                        mensaje = MensajesAuth.REGISTRO_COMPLETADO,
                        registroCompletado = true
                    )
                } else {
                    estado = estado.copy(
                        cargando = false,
                        mensaje = MensajesAuth.KYC_NO_APROBADO
                    )
                }
            }

            is ResultadoApi.Fallo -> estado = estado.copy(
                cargando = false,
                mensaje = when {
                    resultado.http == 202 -> MensajesAuth.KYC_PENDIENTE
                    resultado.mensaje != null -> resultado.mensaje
                    else -> MensajesAuth.ERROR_GENERICO
                }
            )

            ResultadoApi.SinConexion -> estado = estado.copy(
                cargando = false,
                mensaje = MensajesAuth.SIN_CONEXION
            )
        }
    }

    fun consumirRegistroCompletado() {
        if (estado.registroCompletado) estado = estado.copy(registroCompletado = false)
    }

    suspend fun ingresarConCredenciales(email: String, password: String) {
        if (estado.cargando) return
        estado = estado.copy(cargando = true, mensaje = null)

        when (val resultado = gateway.login(email.trim(), password)) {
            is ResultadoApi.Exito -> {
                // Un refresh token guardado antes pertenece a otra sesión: se descarta.
                if (boveda.tieneSesionGuardada()) boveda.borrar()
                abrirSesion(resultado.valor, ofrecerBiometria = biometriaDisponible())
            }

            is ResultadoApi.Fallo -> estado = estado.copy(
                cargando = false,
                mensaje = when (resultado.http) {
                    401 -> MensajesAuth.CREDENCIALES_INVALIDAS
                    else -> resultado.mensaje ?: MensajesAuth.ERROR_GENERICO
                }
            )

            ResultadoApi.SinConexion -> estado = estado.copy(
                cargando = false,
                mensaje = MensajesAuth.SIN_CONEXION
            )
        }
    }

    /**
     * Decide si se debe mostrar el diálogo biométrico. Si la huella no está activada,
     * lleva al usuario al ingreso con credenciales.
     */
    fun solicitarIngresoBiometrico(): Boolean {
        if (estado.cargando) return false
        if (!boveda.tieneSesionGuardada()) {
            estado = estado.copy(
                biometriaActivada = false,
                requiereCredenciales = true,
                mensaje = MensajesAuth.BIOMETRIA_NO_ACTIVADA
            )
            return false
        }
        estado = estado.copy(mensaje = null)
        return true
    }

    /** Se llama cuando el diálogo biométrico terminó con éxito. */
    suspend fun ingresarConBiometria() {
        if (estado.cargando) return
        estado = estado.copy(cargando = true, mensaje = null)

        val refreshGuardado = try {
            boveda.leer()
        } catch (error: LlaveInvalidadaException) {
            descartarBoveda(MensajesAuth.BIOMETRIA_CAMBIO)
            return
        } catch (error: AutenticacionVencidaException) {
            estado = estado.copy(cargando = false, mensaje = MensajesAuth.REINTENTAR_BIOMETRIA)
            return
        }

        when (val resultado = gateway.renovar(refreshGuardado)) {
            is ResultadoApi.Exito -> {
                val nuevos = resultado.valor
                val guardado = try {
                    boveda.guardar(nuevos.refreshToken)
                    true
                } catch (error: Exception) {
                    boveda.borrar()
                    false
                }
                estado = estado.copy(biometriaActivada = guardado)
                abrirSesion(nuevos, ofrecerBiometria = false)
            }

            is ResultadoApi.Fallo -> when (resultado.http) {
                401, 403 -> descartarBoveda(
                    if (resultado.http == 403) {
                        resultado.mensaje ?: MensajesAuth.SESION_GUARDADA_INVALIDA
                    } else {
                        MensajesAuth.SESION_GUARDADA_INVALIDA
                    }
                )

                else -> estado = estado.copy(
                    cargando = false,
                    mensaje = resultado.mensaje ?: MensajesAuth.ERROR_GENERICO
                )
            }

            ResultadoApi.SinConexion -> estado = estado.copy(
                cargando = false,
                mensaje = MensajesAuth.SIN_CONEXION
            )
        }
    }

    /** El diálogo biométrico terminó con error (cancelado, bloqueado, sin hardware...). */
    fun falloBiometrico(fallo: FalloBiometrico) {
        estado = when (fallo) {
            FalloBiometrico.Bloqueado -> estado.copy(
                requiereCredenciales = true,
                mensaje = MensajesAuth.BIOMETRIA_BLOQUEADA
            )

            FalloBiometrico.NoDisponible -> estado.copy(
                requiereCredenciales = true,
                mensaje = MensajesAuth.BIOMETRIA_NO_DISPONIBLE
            )

            FalloBiometrico.UsarCredenciales -> estado.copy(requiereCredenciales = true, mensaje = null)
            FalloBiometrico.Cancelado -> estado.copy(mensaje = null)
            is FalloBiometrico.Reintentable -> estado.copy(mensaje = fallo.mensaje)
        }
    }

    /** La huella no coincidió; el diálogo sigue abierto y permite otro intento. */
    fun huellaNoReconocida() {
        estado = estado.copy(mensaje = MensajesAuth.HUELLA_NO_RECONOCIDA)
    }

    /** El usuario pidió activar la huella desde el inicio (por ejemplo, tras decir "Ahora no"). */
    fun solicitarActivacion() {
        if (tokens == null || boveda.tieneSesionGuardada() || !biometriaDisponible()) return
        estado = estado.copy(ofrecerActivarBiometria = true, mensaje = null)
    }

    /** Crea la llave antes de mostrar el diálogo de activación. */
    fun prepararActivacion() {
        try {
            boveda.preparar()
        } catch (error: Exception) {
            estado = estado.copy(ofrecerActivarBiometria = false, mensaje = MensajesAuth.ACTIVACION_FALLIDA)
        }
    }

    /** Se llama cuando el diálogo biométrico de activación terminó con éxito. */
    fun activarBiometria() {
        val refresh = tokens?.refreshToken ?: return
        estado = try {
            boveda.guardar(refresh)
            estado.copy(biometriaActivada = true, ofrecerActivarBiometria = false, mensaje = null)
        } catch (error: Exception) {
            boveda.borrar()
            estado.copy(
                biometriaActivada = false,
                ofrecerActivarBiometria = false,
                mensaje = MensajesAuth.ACTIVACION_FALLIDA
            )
        }
    }

    fun descartarActivacion(mensaje: String? = null) {
        estado = estado.copy(ofrecerActivarBiometria = false, mensaje = mensaje)
    }

    fun credencialesMostradas() {
        if (estado.requiereCredenciales) estado = estado.copy(requiereCredenciales = false)
    }

    fun consumirMensaje() {
        if (estado.mensaje != null) estado = estado.copy(mensaje = null)
    }

    /** Devuelve true si la sesión expiró y se cerró. */
    fun verificarExpiracion(): Boolean {
        val sesion = estado.sesion ?: return false
        if (reloj.ahoraMs() < sesion.expiraEnMs) return false
        sesionExpirada()
        return true
    }

    /**
     * Cierra la sesión en memoria. La bóveda se conserva para que el usuario pueda
     * volver a entrar con su huella.
     */
    fun sesionExpirada() {
        tokens = null
        estado = estado.copy(
            cargando = false,
            sesion = null,
            ofrecerActivarBiometria = false,
            mensaje = MensajesAuth.SESION_EXPIRADA
        )
    }

    /** Vuelve a pedir el perfil; si el backend rechaza el token, la sesión se da por expirada. */
    suspend fun refrescarPerfil() {
        val access = tokens?.accessToken ?: return
        when (val resultado = gateway.perfil(access)) {
            is ResultadoApi.Exito -> estado.sesion?.let { sesion ->
                estado = estado.copy(sesion = sesion.copy(perfil = resultado.valor))
            }

            is ResultadoApi.Fallo -> if (resultado.http == 401) sesionExpirada()
            ResultadoApi.SinConexion -> Unit
        }
    }

    /** Revoca la sesión en el backend y borra todo rastro local, incluida la bóveda. */
    suspend fun cerrarSesion() {
        val refresh = tokens?.refreshToken
        tokens = null
        boveda.borrar()
        estado = EstadoAuth(cargando = true)
        if (refresh != null) gateway.cerrarSesion(refresh)
        estado = EstadoAuth(biometriaActivada = false, mensaje = MensajesAuth.SESION_CERRADA)
    }

    private suspend fun abrirSesion(nuevos: Tokens, ofrecerBiometria: Boolean) {
        when (val perfil = gateway.perfil(nuevos.accessToken)) {
            is ResultadoApi.Exito -> {
                tokens = nuevos
                estado = estado.copy(
                    cargando = false,
                    mensaje = null,
                    requiereCredenciales = false,
                    biometriaActivada = boveda.tieneSesionGuardada(),
                    ofrecerActivarBiometria = ofrecerBiometria && !boveda.tieneSesionGuardada(),
                    sesion = SesionActiva(
                        perfil = perfil.valor,
                        expiraEnMs = reloj.ahoraMs() + nuevos.expiraEnSegundos * 1000
                    )
                )
            }

            is ResultadoApi.Fallo -> {
                tokens = null
                estado = estado.copy(cargando = false, mensaje = perfil.mensaje ?: MensajesAuth.ERROR_GENERICO)
            }

            ResultadoApi.SinConexion -> {
                tokens = null
                estado = estado.copy(cargando = false, mensaje = MensajesAuth.SIN_CONEXION)
            }
        }
    }

    private fun descartarBoveda(mensaje: String) {
        boveda.borrar()
        tokens = null
        estado = estado.copy(
            cargando = false,
            sesion = null,
            biometriaActivada = false,
            requiereCredenciales = true,
            mensaje = mensaje
        )
    }
}
