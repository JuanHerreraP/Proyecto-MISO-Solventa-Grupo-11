package com.example.solventa.domain.polizas

import com.example.solventa.domain.auth.ResultadoApi

fun resumen(
    id: String = "POL-1",
    numero: String = "SOL-VJ-0001",
    estado: EstadoPoliza = EstadoPoliza.VIGENTE,
    nombreRamo: String = "Seguro de viaje"
) = PolizaResumen(
    polizaId = id,
    numeroPoliza = numero,
    ramo = "VIAJE",
    nombreRamo = nombreRamo,
    estado = estado,
    activa = estado == EstadoPoliza.VIGENTE,
    fechaInicio = "2026-10-01",
    fechaFin = "2026-12-31",
    coberturaPrincipal = "Asistencia médica en viaje"
)

fun billeteraDe(vararg polizas: PolizaResumen) = Billetera(
    polizas = polizas.toList(),
    totalVigentes = polizas.count { it.activa },
    totalInactivas = polizas.count { !it.activa }
)

fun certificado(id: String = "POL-1", estado: EstadoPoliza = EstadoPoliza.VIGENTE) = Certificado(
    polizaId = id,
    numeroPoliza = "SOL-VJ-0001",
    nombreRamo = "Seguro de viaje",
    estado = estado,
    activa = estado == EstadoPoliza.VIGENTE,
    titular = "Ana Pérez",
    documentoTitular = "CC ****5678",
    fechaInicio = "2026-10-01",
    fechaFin = "2026-12-31",
    coberturaPrincipal = "Asistencia médica en viaje",
    sumaAsegurada = "40000000.00",
    moneda = "COP",
    contenidoQr = "SOLVENTA|SOL-VJ-0001|a1b2c3d4e5f60718"
)

val ENLACE = EnlaceCompartido(
    url = "https://api.solventa.co/api/v1/certificados-compartidos/abc",
    expiraEn = "2026-10-22T15:00:00Z"
)

class PolizasGatewayFalso : PolizasGateway {
    var respuestaBilletera: ResultadoApi<Billetera> = ResultadoApi.Exito(billeteraDe(resumen()))
    var respuestaCertificado: ResultadoApi<Certificado> = ResultadoApi.Exito(certificado())
    var respuestaCompartir: ResultadoApi<EnlaceCompartido> = ResultadoApi.Exito(ENLACE)

    val tokensUsados = mutableListOf<String>()
    val certificadosPedidos = mutableListOf<String>()
    val compartidos = mutableListOf<String>()

    override suspend fun billetera(accessToken: String): ResultadoApi<Billetera> {
        tokensUsados += accessToken
        return respuestaBilletera
    }

    override suspend fun certificado(accessToken: String, polizaId: String): ResultadoApi<Certificado> {
        tokensUsados += accessToken
        certificadosPedidos += polizaId
        return respuestaCertificado
    }

    override suspend fun compartir(accessToken: String, polizaId: String): ResultadoApi<EnlaceCompartido> {
        tokensUsados += accessToken
        compartidos += polizaId
        return respuestaCompartir
    }
}

class SesionFalsa(var token: String? = "access-1") : SesionAutenticada {
    var rechazos = 0

    override fun accessTokenVigente(): String? = token

    override fun sesionRechazada() {
        rechazos++
        token = null
    }
}
