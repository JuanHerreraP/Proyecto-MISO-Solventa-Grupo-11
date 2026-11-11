package com.example.solventa.domain.polizas

import com.example.solventa.domain.auth.ResultadoApi

/** Estado que el backend calcula para la billetera (HU07). */
enum class EstadoPoliza { VIGENTE, VENCIDA, CANCELADA }

/** Lo que la billetera muestra de cada póliza. Las fechas llegan en ISO (aaaa-mm-dd). */
data class PolizaResumen(
    val polizaId: String,
    val numeroPoliza: String,
    val ramo: String,
    val nombreRamo: String,
    val estado: EstadoPoliza,
    val activa: Boolean,
    val fechaInicio: String,
    val fechaFin: String,
    val coberturaPrincipal: String,
    /** Fecha de emisión en ISO 8601. El backend ya devuelve la lista con la más reciente arriba. */
    val emitidaEn: String
)

data class Billetera(
    val polizas: List<PolizaResumen>,
    val totalVigentes: Int,
    val totalInactivas: Int
) {
    val vigentes: List<PolizaResumen> get() = polizas.filter { it.activa }
    val inactivas: List<PolizaResumen> get() = polizas.filterNot { it.activa }
    val vacia: Boolean get() = polizas.isEmpty()
}

/** Certificado digital. El documento del titular ya llega enmascarado desde el backend. */
data class Certificado(
    val polizaId: String,
    val numeroPoliza: String,
    val nombreRamo: String,
    val estado: EstadoPoliza,
    val activa: Boolean,
    val titular: String,
    val documentoTitular: String,
    val fechaInicio: String,
    val fechaFin: String,
    val coberturaPrincipal: String,
    val descripcionCobertura: String? = null,
    val sumaAsegurada: String,
    val moneda: String,
    val contenidoQr: String,
    val ramo: String = "",
    val primaTotal: String = "",
    val emitidaEn: String = "",
    val exclusionesPrincipales: List<String> = emptyList()
)

/** Cambio contractual registrado dentro de un endoso. */
data class CambioEndoso(
    val tipo: String,
    val descripcion: String
)

/** Movimiento contractual confirmado. Las fechas llegan en ISO 8601. */
data class EndosoPoliza(
    val endosoId: String,
    val numero: Int,
    val tipo: String,
    val fechaEfecto: String,
    val creadoEn: String,
    val cambios: List<CambioEndoso>,
    val huellaDocumento: String
)

data class HistorialEndosos(val endosos: List<EndosoPoliza>)

/** Categoría del movimiento consolidado del historial de la póliza (HU25). */
enum class CategoriaMovimiento { FINANCIERO, CONTRACTUAL, POLIZA }

/** Tipo de movimiento consolidado del historial de la póliza (HU25). */
enum class TipoMovimiento {
    EMISION,
    PAGO_PRIMA_INICIAL,
    ENDOSO,
    RENOVACION,
    CANCELACION,
    DESEMBOLSO_INDEMNIZACION,
    REEMBOLSO
}

/** Naturaleza del monto de un movimiento; define el signo que se muestra. */
enum class NaturalezaMonto { COBRO, REEMBOLSO, INDEMNIZACION, AJUSTE }

/** Cambio contractual registrado dentro de un movimiento del historial consolidado. */
data class CambioMovimiento(
    val tipo: String,
    val descripcion: String,
    val antes: Map<String, String>?,
    val despues: Map<String, String>?
)

/** Movimiento consolidado del historial de la póliza. Las fechas llegan en ISO 8601. */
data class MovimientoPoliza(
    val movimientoId: String,
    val polizaId: String,
    val categoria: CategoriaMovimiento,
    val tipo: TipoMovimiento,
    val fecha: String,
    val descripcion: String,
    val referencia: String?,
    val referenciaExterna: String?,
    val estado: String?,
    val monto: String?,
    val moneda: String?,
    val naturalezaMonto: NaturalezaMonto?,
    val cambios: List<CambioMovimiento>
)

/**
 * Historial consolidado de movimientos de una póliza (HU25): emisión, pago de prima inicial,
 * endosos, desembolsos y demás. El backend ya ordena los movimientos del más reciente al más antiguo.
 */
data class HistorialPoliza(
    val polizaId: String,
    val numeroPoliza: String,
    val nombreRamo: String,
    val estado: String,
    val movimientos: List<MovimientoPoliza>
)

/** PDF autenticado descargado del backend, todavía sin persistir en el dispositivo. */
class DocumentoPoliza(
    val nombreArchivo: String,
    val contenido: ByteArray,
    val huellaSha256: String
)

/** Enlace temporal para compartir el certificado. [expiraEn] llega en ISO 8601. */
data class EnlaceCompartido(
    val url: String,
    val expiraEn: String
)

/** Vigencia de una póliza; las fechas llegan en ISO (aaaa-mm-dd). */
data class VigenciaRenovacion(val inicio: String, val fin: String)

data class CoberturaRenovacion(val nombre: String, val principal: Boolean)

/** Motivo por el que la póliza no se puede renovar ahora. */
data class BloqueoRenovacion(val codigo: String, val mensaje: String)

/** Renovación creada que espera el pago de [cotizacionId] por [primaTotal]. */
data class RenovacionEnCurso(
    val renovacionId: String,
    val polizaId: String,
    val cotizacionId: String,
    val estado: String,
    val nuevoInicio: String,
    val nuevoFin: String,
    val primaTotal: String,
    val moneda: String
)

/** Lo que el cliente revisa antes de confirmar y pagar la renovación (HU22). */
data class PropuestaRenovacion(
    val polizaId: String,
    val renovable: Boolean,
    val bloqueos: List<BloqueoRenovacion>,
    val nuevaVigencia: VigenciaRenovacion?,
    val coberturas: List<CoberturaRenovacion>,
    val primaNueva: String?,
    val moneda: String,
    val renovacion: RenovacionEnCurso?
)

data class MotivoCancelacion(val codigo: String, val etiqueta: String)

/** Motivo por el que la póliza no se puede cancelar ahora (p. ej. un siniestro en trámite). */
data class BloqueoCancelacion(val codigo: String, val mensaje: String)

/** Lo que el cliente revisa antes de confirmar la cancelación (HU22). */
data class PropuestaCancelacion(
    val polizaId: String,
    val numeroPoliza: String,
    val cancelable: Boolean,
    val bloqueos: List<BloqueoCancelacion>,
    val saldoEstimado: String,
    val moneda: String,
    val motivos: List<MotivoCancelacion>
)

data class CancelacionRealizada(
    val cancelacionId: String,
    val polizaId: String,
    val saldoEstimado: String,
    val moneda: String
)

/** Puerto hacia el backend de la billetera. */
interface PolizasGateway {
    suspend fun billetera(accessToken: String): ResultadoApi<Billetera>
    suspend fun certificado(accessToken: String, polizaId: String): ResultadoApi<Certificado>
    suspend fun historialPoliza(
        accessToken: String,
        polizaId: String
    ): ResultadoApi<HistorialPoliza>
    suspend fun documento(accessToken: String, polizaId: String): ResultadoApi<DocumentoPoliza>
    suspend fun compartir(accessToken: String, polizaId: String): ResultadoApi<EnlaceCompartido>
    suspend fun propuestaRenovacion(
        accessToken: String,
        polizaId: String
    ): ResultadoApi<PropuestaRenovacion>
    suspend fun iniciarRenovacion(
        accessToken: String,
        polizaId: String
    ): ResultadoApi<RenovacionEnCurso>
    suspend fun propuestaCancelacion(
        accessToken: String,
        polizaId: String
    ): ResultadoApi<PropuestaCancelacion>
    suspend fun cancelarPoliza(
        accessToken: String,
        polizaId: String,
        motivo: String
    ): ResultadoApi<CancelacionRealizada>
}

/**
 * Entrega el access token de la sesión activa sin exponerlo a la UI. Lo implementa el
 * coordinador de autenticación, que es el único que guarda los tokens.
 */
interface SesionAutenticada {
    /** Null si no hay sesión o si el token ya venció. */
    fun accessTokenVigente(): String?

    /** El backend rechazó el token: la sesión se cierra en memoria. */
    fun sesionRechazada()
}
