package com.example.solventa.domain.auth

data class SesionActiva(
    val perfil: Perfil,
    val expiraEnMs: Long
)

/**
 * Estado que observa la UI. Los tokens nunca salen del [AuthCoordinator]:
 * la UI solo recibe el perfil, y solo cuando la autenticación terminó bien.
 */
data class EstadoAuth(
    val cargando: Boolean = false,
    val sesion: SesionActiva? = null,
    val mensaje: String? = null,
    val biometriaActivada: Boolean = false,
    val ofrecerActivarBiometria: Boolean = false,
    /** Evento: la UI debe llevar al usuario al ingreso con correo y contraseña. */
    val requiereCredenciales: Boolean = false
)

object MensajesAuth {
    const val SIN_CONEXION = "No pudimos conectarnos con Solventa. Revisa tu conexión e inténtalo de nuevo."
    const val CREDENCIALES_INVALIDAS = "El correo electrónico o la contraseña son incorrectos."
    const val ERROR_GENERICO = "Algo salió mal. Inténtalo de nuevo en unos minutos."
    const val BIOMETRIA_NO_ACTIVADA =
        "Ingresa una vez con tu correo y contraseña para activar el ingreso con huella."
    const val BIOMETRIA_CAMBIO =
        "Detectamos un cambio en la biometría del dispositivo. Ingresa con tu correo y contraseña para volver a activarla."
    const val SESION_GUARDADA_INVALIDA =
        "Tu sesión guardada ya no es válida. Ingresa con tu correo y contraseña."
    const val SESION_EXPIRADA = "Tu sesión expiró. Vuelve a ingresar."
    const val SESION_CERRADA = "Cerraste sesión."
    const val REINTENTAR_BIOMETRIA = "No pudimos validar tu huella a tiempo. Inténtalo de nuevo."
    const val ACTIVACION_FALLIDA = "No pudimos activar el ingreso con huella. Inténtalo más tarde."
    const val BIOMETRIA_BLOQUEADA =
        "Superaste los intentos permitidos con huella. Ingresa con tu correo y contraseña."
    const val BIOMETRIA_NO_DISPONIBLE =
        "La biometría no está disponible en este momento. Ingresa con tu correo y contraseña."
    const val HUELLA_NO_RECONOCIDA = "No reconocimos tu huella. Inténtalo de nuevo."
}
