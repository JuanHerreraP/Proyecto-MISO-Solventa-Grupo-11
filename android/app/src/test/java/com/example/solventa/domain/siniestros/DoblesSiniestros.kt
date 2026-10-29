package com.example.solventa.domain.siniestros

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.SesionAutenticada

fun siniestro(
    id: String = "SIN-1",
    polizaId: String = "DEMO-04",
    origen: OrigenSiniestro = OrigenSiniestro.AUTOMATICO,
    estado: EstadoSiniestro = EstadoSiniestro.REGISTRADO,
    eventoId: String? = "FLIGHT-AV123-20261026-abc"
) = Siniestro(
    siniestroId = id,
    polizaId = polizaId,
    origen = origen,
    estado = estado,
    eventoId = eventoId,
    fechaEvento = "2026-10-26",
    horaEvento = "20:00:00",
    lugar = "BOG",
    descripcion = "Siniestro paramétrico automático por evento RETRASO_VUELO.",
    estimacionDanos = "500000.00",
    moneda = "COP",
    registradoEn = "2026-10-26T20:01:00Z"
)

fun siniestrosDe(vararg items: Siniestro) = Siniestros(items.toList())

fun solicitud(
    polizaId: String = "POL-1",
    fecha: String = "2026-10-20",
    hora: String = "18:30:00",
    lugar: String = "Aeropuerto El Dorado",
    descripcion: String = "El vuelo fue cancelado y hubo gastos adicionales.",
    estimacion: String = "850000"
) = SolicitudSiniestro(
    polizaId = polizaId,
    fechaEvento = fecha,
    horaEvento = hora,
    lugar = lugar,
    descripcion = descripcion,
    estimacionDanos = estimacion
)

class SiniestrosGatewayFalso : SiniestrosGateway {
    var respuesta: ResultadoApi<Siniestros> = ResultadoApi.Exito(siniestrosDe(siniestro()))
    var respuestaRegistro: ResultadoApi<Siniestro> = ResultadoApi.Exito(siniestro(id = "SIN-NUEVO"))
    val tokensUsados = mutableListOf<String>()
    val solicitudes = mutableListOf<SolicitudSiniestro>()

    override suspend fun listar(accessToken: String): ResultadoApi<Siniestros> {
        tokensUsados += accessToken
        return respuesta
    }

    override suspend fun registrar(
        accessToken: String,
        solicitud: SolicitudSiniestro
    ): ResultadoApi<Siniestro> {
        tokensUsados += accessToken
        solicitudes += solicitud
        return respuestaRegistro
    }
}

class SesionSiniestrosFalsa(var token: String? = "access-1") : SesionAutenticada {
    var rechazos = 0

    override fun accessTokenVigente(): String? = token

    override fun sesionRechazada() {
        rechazos++
        token = null
    }
}
