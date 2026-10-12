package com.example.solventa.domain.auth

import kotlin.coroutines.Continuation
import kotlin.coroutines.EmptyCoroutineContext
import kotlin.coroutines.startCoroutine

/** Ejecuta una función suspendida cuyos dobles responden de inmediato. */
fun ejecutar(bloque: suspend () -> Unit) {
    var resultado: Result<Unit>? = null
    bloque.startCoroutine(Continuation(EmptyCoroutineContext) { resultado = it })
    checkNotNull(resultado) { "La corrutina quedó suspendida; los dobles deben responder de inmediato." }
        .getOrThrow()
}

val PERFIL_ANA = Perfil(
    id = "u-1",
    nombre = "Ana",
    apellido = "Pérez",
    email = "ana@gmail.com",
    rol = "CLIENTE"
)

fun tokens(n: Int, expiraEnSegundos: Long = 1800) = Tokens(
    accessToken = "access-$n",
    refreshToken = "refresh-$n",
    expiraEnSegundos = expiraEnSegundos
)

class GatewayFalso : AuthGateway {
    var respuestaLogin: ResultadoApi<Tokens> = ResultadoApi.Exito(tokens(1))
    var respuestaRenovar: ResultadoApi<Tokens> = ResultadoApi.Exito(tokens(2))
    var respuestaPerfil: ResultadoApi<Perfil> = ResultadoApi.Exito(PERFIL_ANA)

    val renovados = mutableListOf<String>()
    val cerrados = mutableListOf<String>()
    val perfilesPedidos = mutableListOf<String>()

    override suspend fun login(email: String, password: String) = respuestaLogin

    override suspend fun renovar(refreshToken: String): ResultadoApi<Tokens> {
        renovados += refreshToken
        return respuestaRenovar
    }

    override suspend fun cerrarSesion(refreshToken: String): ResultadoApi<Unit> {
        cerrados += refreshToken
        return ResultadoApi.Exito(Unit)
    }

    override suspend fun perfil(accessToken: String): ResultadoApi<Perfil> {
        perfilesPedidos += accessToken
        return respuestaPerfil
    }
}

class BovedaFalsa(var guardado: String? = null) : BovedaSesion {
    var errorAlLeer: Exception? = null
    var errorAlGuardar: Exception? = null
    var preparada = false
    var borrados = 0

    override fun tieneSesionGuardada() = guardado != null

    override fun preparar() {
        preparada = true
    }

    override fun guardar(refreshToken: String) {
        errorAlGuardar?.let { throw it }
        guardado = refreshToken
    }

    override fun leer(): String {
        errorAlLeer?.let { throw it }
        return checkNotNull(guardado)
    }

    override fun borrar() {
        borrados++
        guardado = null
    }
}

class RelojFalso(var ahora: Long = 1_000_000L) : Reloj {
    override fun ahoraMs() = ahora
}
