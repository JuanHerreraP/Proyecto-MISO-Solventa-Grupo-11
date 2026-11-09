package com.example.solventa.data.remote

import com.example.solventa.domain.polizas.Billetera
import com.example.solventa.domain.polizas.CambioEndoso
import com.example.solventa.domain.polizas.CambioMovimiento
import com.example.solventa.domain.polizas.CategoriaMovimiento
import com.example.solventa.domain.polizas.Certificado
import com.example.solventa.domain.polizas.EndosoPoliza
import com.example.solventa.domain.polizas.EnlaceCompartido
import com.example.solventa.domain.polizas.EstadoPoliza
import com.example.solventa.domain.polizas.HistorialEndosos
import com.example.solventa.domain.polizas.HistorialPoliza
import com.example.solventa.domain.polizas.MovimientoPoliza
import com.example.solventa.domain.polizas.NaturalezaMonto
import com.example.solventa.domain.polizas.PolizaResumen
import com.example.solventa.domain.polizas.TipoMovimiento
import com.google.gson.annotations.SerializedName

/**
 * Gson no pasa por el constructor de Kotlin: un campo ausente llega como null aunque el tipo
 * no lo permita. Por eso los DTO son anulables y el mapeo descarta lo incompleto.
 */
data class PolizaEnBilleteraDto(
    @SerializedName("poliza_id") val polizaId: String?,
    @SerializedName("numero_poliza") val numeroPoliza: String?,
    @SerializedName("ramo") val ramo: String?,
    @SerializedName("nombre_ramo") val nombreRamo: String?,
    @SerializedName("estado") val estado: String?,
    @SerializedName("activa") val activa: Boolean?,
    @SerializedName("fecha_inicio") val fechaInicio: String?,
    @SerializedName("fecha_fin") val fechaFin: String?,
    @SerializedName("cobertura_principal") val coberturaPrincipal: String?,
    @SerializedName("emitida_en") val emitidaEn: String?
) {
    fun aPoliza(): PolizaResumen? {
        val estadoPoliza = estado.aEstado() ?: return null
        return PolizaResumen(
            polizaId = polizaId ?: return null,
            numeroPoliza = numeroPoliza ?: return null,
            ramo = ramo.orEmpty(),
            nombreRamo = nombreRamo ?: ramo.orEmpty(),
            estado = estadoPoliza,
            activa = activa ?: (estadoPoliza == EstadoPoliza.VIGENTE),
            fechaInicio = fechaInicio ?: return null,
            fechaFin = fechaFin ?: return null,
            coberturaPrincipal = coberturaPrincipal.orEmpty(),
            emitidaEn = emitidaEn.orEmpty()
        )
    }
}

data class BilleteraDto(
    @SerializedName("polizas") val polizas: List<PolizaEnBilleteraDto>?,
    @SerializedName("total_vigentes") val totalVigentes: Int?,
    @SerializedName("total_inactivas") val totalInactivas: Int?
) {
    fun aBilletera(): Billetera {
        val lista = polizas.orEmpty().mapNotNull { it.aPoliza() }
        return Billetera(
            polizas = lista,
            totalVigentes = lista.count { it.activa },
            totalInactivas = lista.count { !it.activa }
        )
    }
}

data class CertificadoDto(
    @SerializedName("poliza_id") val polizaId: String?,
    @SerializedName("numero_poliza") val numeroPoliza: String?,
    @SerializedName("ramo") val ramo: String?,
    @SerializedName("nombre_ramo") val nombreRamo: String?,
    @SerializedName("estado") val estado: String?,
    @SerializedName("activa") val activa: Boolean?,
    @SerializedName("titular") val titular: String?,
    @SerializedName("documento_titular") val documentoTitular: String?,
    @SerializedName("fecha_inicio") val fechaInicio: String?,
    @SerializedName("fecha_fin") val fechaFin: String?,
    @SerializedName("cobertura_principal") val coberturaPrincipal: String?,
    @SerializedName("descripcion_cobertura") val descripcionCobertura: String?,
    @SerializedName("exclusiones_principales") val exclusionesPrincipales: List<String>?,
    @SerializedName("suma_asegurada") val sumaAsegurada: String?,
    @SerializedName("prima_total") val primaTotal: String?,
    @SerializedName("moneda") val moneda: String?,
    @SerializedName("emitida_en") val emitidaEn: String?,
    @SerializedName("contenido_qr") val contenidoQr: String?
) {
    fun aCertificado(): Certificado? {
        val estadoPoliza = estado.aEstado() ?: return null
        return Certificado(
            polizaId = polizaId ?: return null,
            numeroPoliza = numeroPoliza ?: return null,
            nombreRamo = nombreRamo.orEmpty(),
            estado = estadoPoliza,
            activa = activa ?: (estadoPoliza == EstadoPoliza.VIGENTE),
            titular = titular.orEmpty(),
            documentoTitular = documentoTitular.orEmpty(),
            fechaInicio = fechaInicio ?: return null,
            fechaFin = fechaFin ?: return null,
            coberturaPrincipal = coberturaPrincipal.orEmpty(),
            descripcionCobertura = descripcionCobertura,
            sumaAsegurada = sumaAsegurada.orEmpty(),
            moneda = moneda ?: "COP",
            contenidoQr = contenidoQr ?: return null,
            ramo = ramo.orEmpty(),
            primaTotal = primaTotal.orEmpty(),
            emitidaEn = emitidaEn.orEmpty(),
            exclusionesPrincipales = exclusionesPrincipales.orEmpty().filter { it.isNotBlank() }
        )
    }
}

data class CambioEndosoDto(
    @SerializedName("tipo") val tipo: String?,
    @SerializedName("descripcion") val descripcion: String?
) {
    fun aCambio(): CambioEndoso? {
        return CambioEndoso(
            tipo = tipo ?: return null,
            descripcion = descripcion ?: return null
        )
    }
}

data class EndosoPolizaDto(
    @SerializedName("endoso_id") val endosoId: String?,
    @SerializedName("numero_endoso") val numero: Int?,
    @SerializedName("tipo") val tipo: String?,
    @SerializedName("fecha_efecto") val fechaEfecto: String?,
    @SerializedName("creado_en") val creadoEn: String?,
    @SerializedName("cambios") val cambios: List<CambioEndosoDto>?,
    @SerializedName("huella_documento") val huellaDocumento: String?
) {
    fun aEndoso(): EndosoPoliza? {
        return EndosoPoliza(
            endosoId = endosoId ?: return null,
            numero = numero ?: return null,
            tipo = tipo ?: return null,
            fechaEfecto = fechaEfecto ?: return null,
            creadoEn = creadoEn ?: return null,
            cambios = cambios.orEmpty().mapNotNull { it.aCambio() },
            huellaDocumento = huellaDocumento ?: return null
        )
    }
}

data class HistorialEndososDto(
    @SerializedName("endosos") val endosos: List<EndosoPolizaDto>?
) {
    fun aHistorial() = HistorialEndosos(endosos.orEmpty().mapNotNull { it.aEndoso() })
}

/**
 * Historial consolidado de movimientos de la póliza (HU25). Gson puede dejar cualquier campo
 * en null; el mapeo descarta lo incompleto para no romper la pantalla.
 */
data class CambioMovimientoDto(
    @SerializedName("tipo") val tipo: String?,
    @SerializedName("descripcion") val descripcion: String?,
    @SerializedName("antes") val antes: Map<String, String>?,
    @SerializedName("despues") val despues: Map<String, String>?
) {
    fun aCambio(): CambioMovimiento? {
        return CambioMovimiento(
            tipo = tipo ?: return null,
            descripcion = descripcion ?: return null,
            antes = antes,
            despues = despues
        )
    }
}

data class MovimientoPolizaDto(
    @SerializedName("movimiento_id") val movimientoId: String?,
    @SerializedName("poliza_id") val polizaId: String?,
    @SerializedName("categoria") val categoria: String?,
    @SerializedName("tipo") val tipo: String?,
    @SerializedName("fecha") val fecha: String?,
    @SerializedName("descripcion") val descripcion: String?,
    @SerializedName("referencia") val referencia: String?,
    @SerializedName("referencia_externa") val referenciaExterna: String?,
    @SerializedName("estado") val estado: String?,
    @SerializedName("monto") val monto: String?,
    @SerializedName("moneda") val moneda: String?,
    @SerializedName("naturaleza_monto") val naturalezaMonto: String?,
    @SerializedName("cambios") val cambios: List<CambioMovimientoDto>?
) {
    fun aMovimiento(): MovimientoPoliza? {
        return MovimientoPoliza(
            movimientoId = movimientoId ?: return null,
            polizaId = polizaId ?: return null,
            categoria = categoria.aCategoriaMovimiento() ?: return null,
            tipo = tipo.aTipoMovimiento() ?: return null,
            fecha = fecha ?: return null,
            descripcion = descripcion ?: return null,
            referencia = referencia,
            referenciaExterna = referenciaExterna,
            estado = estado,
            monto = monto,
            moneda = moneda,
            naturalezaMonto = naturalezaMonto.aNaturalezaMonto(),
            cambios = cambios.orEmpty().mapNotNull { it.aCambio() }
        )
    }
}

data class HistorialPolizaDto(
    @SerializedName("poliza_id") val polizaId: String?,
    @SerializedName("numero_poliza") val numeroPoliza: String?,
    @SerializedName("nombre_ramo") val nombreRamo: String?,
    @SerializedName("estado") val estado: String?,
    @SerializedName("movimientos") val movimientos: List<MovimientoPolizaDto>?
) {
    fun aHistorial(): HistorialPoliza? {
        return HistorialPoliza(
            polizaId = polizaId ?: return null,
            numeroPoliza = numeroPoliza ?: return null,
            nombreRamo = nombreRamo.orEmpty(),
            estado = estado.orEmpty(),
            movimientos = movimientos.orEmpty().mapNotNull { it.aMovimiento() }
        )
    }
}

data class EnlaceCompartidoDto(
    @SerializedName("url") val url: String?,
    @SerializedName("expira_en") val expiraEn: String?
) {
    fun aEnlace(): EnlaceCompartido? {
        val direccion = url?.takeIf { it.startsWith("https://") || it.startsWith("http://") }
            ?: return null
        return EnlaceCompartido(url = direccion, expiraEn = expiraEn.orEmpty())
    }
}

private fun String?.aEstado(): EstadoPoliza? =
    this?.let { valor -> EstadoPoliza.entries.firstOrNull { it.name == valor } }

private fun String?.aCategoriaMovimiento(): CategoriaMovimiento? =
    this?.let { valor -> CategoriaMovimiento.entries.firstOrNull { it.name == valor } }

private fun String?.aTipoMovimiento(): TipoMovimiento? =
    this?.let { valor -> TipoMovimiento.entries.firstOrNull { it.name == valor } }

private fun String?.aNaturalezaMonto(): NaturalezaMonto? =
    this?.let { valor -> NaturalezaMonto.entries.firstOrNull { it.name == valor } }
