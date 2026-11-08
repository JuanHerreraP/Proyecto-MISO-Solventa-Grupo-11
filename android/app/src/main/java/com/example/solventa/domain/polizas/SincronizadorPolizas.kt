package com.example.solventa.domain.polizas

import kotlinx.coroutines.delay

/** Reintenta una sincronización recuperable sin bloquear el uso de la aplicación. */
class SincronizadorPolizas(
    private val sincronizar: suspend () -> ResultadoSincronizacion,
    private val alFalloPersistente: () -> Unit,
    private val esperar: suspend (Long) -> Unit = { delay(it) },
    private val intentosMaximos: Int = 3,
    private val esperaInicialMs: Long = 2_000L
) {
    init {
        require(intentosMaximos > 0)
        require(esperaInicialMs >= 0)
    }

    suspend fun ejecutar() {
        var esperaMs = esperaInicialMs
        repeat(intentosMaximos) { intento ->
            when (sincronizar()) {
                ResultadoSincronizacion.EXITO,
                ResultadoSincronizacion.SIN_SESION,
                ResultadoSincronizacion.EN_CURSO -> return

                ResultadoSincronizacion.REINTENTAR -> {
                    if (intento == intentosMaximos - 1) {
                        alFalloPersistente()
                        return
                    }
                    esperar(esperaMs)
                    esperaMs *= 2
                }
            }
        }
    }
}
