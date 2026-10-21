package com.example.solventa.domain.cotizaciones

/** Ramos aceptados por el contrato de cotizaciones del backend. */
enum class RamoCotizacion(val codigoApi: String) {
    VIAJE("VIAJE"),
    DISPOSITIVOS("PROTECCION_DISPOSITIVOS"),
    VIDA("VIDA"),
    PARAMETRICO("PARAMETRICO")
}
