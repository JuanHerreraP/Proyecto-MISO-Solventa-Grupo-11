package com.example.solventa.domain.siniestros

import com.example.solventa.domain.auth.ResultadoApi

/** Origen del siniestro. AUTOMATICO llega de la telemetría externa (HU20); MANUAL lo reporta el cliente. */
enum class OrigenSiniestro { MANUAL, AUTOMATICO }

/** Ciclo de vida del siniestro tal como lo calcula el backend (HU20). */
enum class EstadoSiniestro { REGISTRADO, EN_EVALUACION, APROBADO, RECHAZADO }

/**
 * Un siniestro del cliente. Las fechas llegan en ISO (aaaa-mm-dd y aaaa-mm-ddThh:mm:ssZ).
 * [eventoId] solo viene cuando el origen es AUTOMATICO (identificador del evento de telemetría).
 */
data class Siniestro(
    val siniestroId: String,
    val polizaId: String,
    val origen: OrigenSiniestro,
    val estado: EstadoSiniestro,
    val eventoId: String?,
    val fechaEvento: String,
    val horaEvento: String,
    val lugar: String,
    val descripcion: String,
    val estimacionDanos: String,
    val moneda: String,
    val registradoEn: String
)

/** Lo que la pantalla de siniestros muestra: la lista, del más reciente al más antiguo. */
data class Siniestros(
    val siniestros: List<Siniestro>
) {
    val vacia: Boolean get() = siniestros.isEmpty()
    val total: Int get() = siniestros.size
    val automaticos: Int get() = siniestros.count { it.origen == OrigenSiniestro.AUTOMATICO }
}

/** Puerto hacia el backend de siniestros. El backend filtra por la identidad del token. */
interface SiniestrosGateway {
    suspend fun listar(accessToken: String): ResultadoApi<Siniestros>

    suspend fun registrar(
        accessToken: String,
        solicitud: SolicitudSiniestro
    ): ResultadoApi<Siniestro>
}

/**
 * Datos del registro manual de un siniestro (HU20). El cliente nunca envía su identificador:
 * el backend lo toma de la sesión. Las fechas van en ISO (aaaa-mm-dd y hh:mm:ss).
 */
data class SolicitudSiniestro(
    val polizaId: String,
    val fechaEvento: String,
    val horaEvento: String,
    val lugar: String,
    val descripcion: String,
    val estimacionDanos: String
)
