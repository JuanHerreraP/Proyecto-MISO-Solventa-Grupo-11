package com.example.solventa.domain.cotizaciones

import java.math.BigDecimal

/** Resultado comercial que la API retorna después de calcular una cotización. */
data class ResultadoCotizacion(
    val cotizacionId: String,
    val ramo: RamoCotizacion,
    val estado: String,
    val primaTotal: BigDecimal,
    val moneda: String,
    val coberturaPrincipal: CoberturaCotizacion,
    val vigenteHasta: String,
    val perfilRiesgoId: String? = null,
    val datosRiesgo: Map<String, String> = emptyMap()
)

data class CoberturaCotizacion(
    val codigo: String,
    val nombre: String,
    val sumaAsegurada: BigDecimal,
    val descripcion: String? = null
)

