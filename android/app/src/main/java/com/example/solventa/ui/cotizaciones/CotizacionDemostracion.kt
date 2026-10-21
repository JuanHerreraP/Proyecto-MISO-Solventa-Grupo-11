package com.example.solventa.ui.cotizaciones

import com.example.solventa.domain.cotizaciones.CoberturaCotizacion
import com.example.solventa.domain.cotizaciones.RamoCotizacion
import com.example.solventa.domain.cotizaciones.ResultadoCotizacion
import java.math.BigDecimal

/** Datos locales que permiten revisar la pantalla antes de conectarla con la API en el paso 5. */
object CotizacionDemostracion {
    fun para(ramo: RamoCotizacion): ResultadoCotizacion = when (ramo) {
        RamoCotizacion.VIAJE -> resultado(
            ramo = ramo,
            prima = "148900",
            codigoCobertura = "ASISTENCIA_VIAJE",
            nombreCobertura = "Asistencia integral de viaje",
            sumaAsegurada = "5000000",
            descripcion = "Atención de emergencias cubiertas durante el viaje contratado."
        )
        RamoCotizacion.DISPOSITIVOS -> resultado(
            ramo = ramo,
            prima = "84000",
            codigoCobertura = "DANO_ROBO_DISPOSITIVO",
            nombreCobertura = "Daño accidental y robo",
            sumaAsegurada = "2000000",
            descripcion = "Protección del dispositivo hasta su valor comercial declarado."
        )
        RamoCotizacion.VIDA -> resultado(
            ramo = ramo,
            prima = "210000",
            codigoCobertura = "FALLECIMIENTO",
            nombreCobertura = "Cobertura por fallecimiento",
            sumaAsegurada = "50000000",
            descripcion = "Pago del valor asegurado a los beneficiarios de la póliza."
        )
        RamoCotizacion.PARAMETRICO -> resultado(
            ramo = ramo,
            prima = "40000",
            codigoCobertura = "COMPENSACION_RETRASO_VUELO",
            nombreCobertura = "Compensación por retraso de vuelo",
            sumaAsegurada = "800000",
            descripcion = "Pago automático cuando el evento supera el umbral contratado."
        )
    }

    private fun resultado(
        ramo: RamoCotizacion,
        prima: String,
        codigoCobertura: String,
        nombreCobertura: String,
        sumaAsegurada: String,
        descripcion: String
    ) = ResultadoCotizacion(
        cotizacionId = "COT-DEMO-${ramo.codigoApi}",
        ramo = ramo,
        estado = "VIGENTE",
        primaTotal = BigDecimal(prima),
        moneda = "COP",
        coberturaPrincipal = CoberturaCotizacion(
            codigo = codigoCobertura,
            nombre = nombreCobertura,
            sumaAsegurada = BigDecimal(sumaAsegurada),
            descripcion = descripcion
        ),
        vigenteHasta = "24 H",
        perfilRiesgoId = "PERFIL-DEMO"
    )
}

