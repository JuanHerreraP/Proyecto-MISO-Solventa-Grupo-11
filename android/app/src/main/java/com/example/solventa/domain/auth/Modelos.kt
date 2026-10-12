package com.example.solventa.domain.auth

/** Tokens que entrega el backend al iniciar o renovar sesión. */
data class Tokens(
    val accessToken: String,
    val refreshToken: String,
    val expiraEnSegundos: Long
)

/** Datos mínimos del usuario autenticado (GET /api/v1/auth/me). */
data class Perfil(
    val id: String,
    val nombre: String,
    val apellido: String,
    val email: String,
    val rol: String
)

/** Resultado de una llamada al backend, sin excepciones hacia la UI. */
sealed interface ResultadoApi<out T> {
    data class Exito<T>(val valor: T) : ResultadoApi<T>

    data class Fallo(
        val http: Int,
        val codigo: String?,
        val mensaje: String?
    ) : ResultadoApi<Nothing>

    data object SinConexion : ResultadoApi<Nothing>
}

inline fun <T, R> ResultadoApi<T>.mapear(transformar: (T) -> R): ResultadoApi<R> = when (this) {
    is ResultadoApi.Exito -> ResultadoApi.Exito(transformar(valor))
    is ResultadoApi.Fallo -> this
    ResultadoApi.SinConexion -> ResultadoApi.SinConexion
}

/** Puerto hacia el backend de identidad. */
interface AuthGateway {
    suspend fun login(email: String, password: String): ResultadoApi<Tokens>
    suspend fun renovar(refreshToken: String): ResultadoApi<Tokens>
    suspend fun cerrarSesion(refreshToken: String): ResultadoApi<Unit>
    suspend fun perfil(accessToken: String): ResultadoApi<Perfil>
}

/**
 * Guarda el refresh token cifrado con una llave del Android Keystore que solo se
 * puede usar justo después de una autenticación biométrica fuerte.
 */
interface BovedaSesion {
    fun tieneSesionGuardada(): Boolean

    /** Crea la llave si no existe. No requiere autenticación. */
    fun preparar()

    /** Requiere una autenticación biométrica reciente. */
    fun guardar(refreshToken: String)

    /** Requiere una autenticación biométrica reciente. */
    fun leer(): String

    fun borrar()
}

/** La llave dejó de servir, por ejemplo porque se registró una huella nueva. */
class LlaveInvalidadaException(causa: Throwable? = null) :
    Exception("La llave de la sesión biométrica ya no es válida.", causa)

/** Pasó la ventana de uso de la llave después de la autenticación biométrica. */
class AutenticacionVencidaException(causa: Throwable? = null) :
    Exception("La autenticación biométrica ya no está vigente.", causa)

fun interface Reloj {
    fun ahoraMs(): Long
}
