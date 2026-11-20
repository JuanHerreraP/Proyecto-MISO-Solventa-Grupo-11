package com.example.solventa.domain.asistencias

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.siniestros.Ubicacion

/**
 * Tipo de servicio de asistencia (HU06). Los nombres coinciden con los códigos del backend.
 * [etiqueta] es el texto visible que se muestra al cliente.
 */
enum class TipoServicio(val etiqueta: String) {
    ASISTENCIA_MEDICA("Atención médica"),
    ASISTENCIA_VIAJERO("Asistencia al viajero"),
    DIAGNOSTICO_TECNICO("Diagnóstico técnico"),
    REPARACION_DISPOSITIVO("Reparación de dispositivo");

    companion object {
        fun desdeCodigo(codigo: String?): TipoServicio? =
            entries.firstOrNull { it.name == codigo }
    }
}

/** Estado de una asistencia tal como lo calcula el backend (HU06). */
enum class EstadoAsistencia(val etiqueta: String) {
    SOLICITADA("Solicitada"),
    ACEPTADA("Aceptada"),
    CANCELADA("Cancelada");

    companion object {
        fun desdeCodigo(codigo: String?): EstadoAsistencia? =
            entries.firstOrNull { it.name == codigo }
    }
}

/** Un servicio de asistencia disponible para una póliza. */
data class ServicioAsistencia(
    val codigo: TipoServicio,
    val nombre: String
)

/** Servicios de asistencia que ofrece una póliza según su ramo. Puede venir vacío (VIDA, PARAMETRICO). */
data class ServiciosPoliza(
    val polizaId: String,
    val ramo: String,
    val servicios: List<ServicioAsistencia>
) {
    val vacia: Boolean get() = servicios.isEmpty()
}

/** Un prestador cercano, con su distancia a la ubicación del cliente. */
data class PrestadorCercano(
    val prestadorId: String,
    val nombre: String,
    val tipoServicio: TipoServicio,
    val direccion: String,
    val telefono: String?,
    val latitud: Double,
    val longitud: Double,
    val distanciaKm: Double
)

/** Resultado de la búsqueda de prestadores cercanos. El backend ya ordena por distancia. */
data class PrestadoresCercanos(
    val polizaId: String,
    val servicio: TipoServicio,
    val latitud: Double,
    val longitud: Double,
    val prestadores: List<PrestadorCercano>
) {
    val vacia: Boolean get() = prestadores.isEmpty()
}

/** Datos de la asistencia a crear. El cliente nunca envía su identificador: lo pone el backend. */
data class NuevaAsistencia(
    val polizaId: String,
    val prestadorId: String,
    val servicio: TipoServicio,
    val latitud: Double,
    val longitud: Double,
    val observaciones: String? = null
)

/** Prestador resumido que viaja en la respuesta de una asistencia. */
data class PrestadorResumen(
    val prestadorId: String,
    val nombre: String,
    val telefono: String?
)

/** Una asistencia del cliente. Las fechas llegan en ISO 8601. */
data class Asistencia(
    val asistenciaId: String,
    val polizaId: String,
    val prestador: PrestadorResumen,
    val servicio: TipoServicio,
    val estado: EstadoAsistencia,
    val latitud: Double,
    val longitud: Double,
    val observaciones: String?,
    val creadaEn: String,
    val canceladaEn: String?,
    /** Seguimiento (HU06 ampliación): null hasta que Operaciones acepte. */
    val aceptadaEn: String? = null,
    /** ETA en minutos; null = "aún no disponible". Nunca 0 para representar ausencia. */
    val tiempoEstimadoLlegadaMinutos: Int? = null
) {
    val cancelable: Boolean get() = estado == EstadoAsistencia.SOLICITADA
    val aceptada: Boolean get() = estado == EstadoAsistencia.ACEPTADA
}

/**
 * Puerto hacia el backend de asistencias (HU06). El backend filtra por la identidad del token:
 * la app nunca envía el identificador del cliente.
 */
interface AsistenciasGateway {
    suspend fun servicios(
        accessToken: String,
        polizaId: String
    ): ResultadoApi<ServiciosPoliza>

    suspend fun prestadoresCercanos(
        accessToken: String,
        polizaId: String,
        servicio: TipoServicio,
        latitud: Double,
        longitud: Double,
        radioKm: Double
    ): ResultadoApi<PrestadoresCercanos>

    suspend fun solicitar(
        accessToken: String,
        solicitud: NuevaAsistencia
    ): ResultadoApi<Asistencia>

    suspend fun listar(accessToken: String): ResultadoApi<List<Asistencia>>

    suspend fun cancelar(
        accessToken: String,
        asistenciaId: String
    ): ResultadoApi<Asistencia>
}

/** Mensajes para la UI de asistencia; ningún texto expone coordenadas. */
object MensajesAsistencias {
    const val SIN_CONEXION =
        "No pudimos conectarnos con Solventa. Revisa tu conexión e inténtalo de nuevo."
    const val ERROR_GENERICO = "Algo salió mal. Inténtalo de nuevo en unos minutos."
    const val SESION_VENCIDA = "Tu sesión expiró. Vuelve a ingresar."

    const val POLIZA_NO_ENCONTRADA = "No encontramos esa póliza en tu billetera."
    const val POLIZA_NO_AUTORIZADA = "No tienes acceso a esta póliza."
    const val POLIZA_NO_VIGENTE = "La póliza no está vigente."
    const val SERVICIO_NO_DISPONIBLE = "Esta póliza no ofrece ese servicio de asistencia."

    const val PRESTADOR_NO_ENCONTRADO = "El prestador ya no está disponible. Elige otro."
    const val PRESTADOR_NO_DISPONIBLE = "El prestador ya no está disponible. Elige otro."
    const val SERVICIO_NO_OFRECIDO =
        "El prestador no ofrece el servicio seleccionado. Elige otro."

    const val SIN_PRESTADORES =
        "No encontramos prestadores disponibles dentro del radio de búsqueda."
    const val SIN_UBICACION =
        "Necesitamos tu ubicación para encontrar prestadores cercanos. Puedes habilitarla " +
            "desde los permisos de Solventa."
    const val UBICACION_NO_DISPONIBLE =
        "No pudimos obtener tu ubicación actual. Revisa que el GPS esté activo e inténtalo de nuevo."
    const val PERMISO_UBICACION =
        "Asistencia necesita tu ubicación para mostrar prestadores cercanos."

    const val SOLICITUD_FALLIDA = "No pudimos solicitar la asistencia. Inténtalo de nuevo."
    const val CANCELACION_FALLIDA = "No pudimos cancelar la asistencia. Inténtalo de nuevo."
    const val ASISTENCIA_NO_ENCONTRADA = "No encontramos esta asistencia."
    const val ASISTENCIA_YA_CANCELADA = "Esta asistencia ya estaba cancelada."
    const val DATOS_INVALIDOS = "Revisa los datos e inténtalo de nuevo."
}

/** Paso visible del flujo de asistencia en sitio (HU06). */
enum class PasoAsistencia {
    SELECCION_POLIZA,
    SELECCION_SERVICIO,
    PERMISO_UBICACION,
    PRESTADORES,
    CONFIRMACION,
    EXITO,
    MIS_ASISTENCIAS
}

/**
 * Estado explícito del flujo de asistencia en sitio (HU06). La pantalla no dispersa el estado
 * en varios `mutableStateOf`: todo vive aquí.
 */
data class EstadoAsistencias(
    val paso: PasoAsistencia = PasoAsistencia.SELECCION_POLIZA,
    val cargando: Boolean = false,
    val polizaSeleccionadaId: String? = null,
    val polizaSeleccionadaEtiqueta: String? = null,
    val servicios: List<ServicioAsistencia> = emptyList(),
    val servicioSeleccionado: ServicioAsistencia? = null,
    val ubicacion: Ubicacion? = null,
    val permisoDenegado: Boolean = false,
    val radioKm: Double = 25.0,
    val prestadores: List<PrestadorCercano> = emptyList(),
    val prestadorSeleccionado: PrestadorCercano? = null,
    val solicitando: Boolean = false,
    val asistenciaCreada: Asistencia? = null,
    val asistencias: List<Asistencia> = emptyList(),
    val cargandoAsistencias: Boolean = false,
    val cancelandoId: String? = null,
    val error: String? = null,
    val aviso: String? = null
)
