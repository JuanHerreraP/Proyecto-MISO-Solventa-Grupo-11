package com.example.solventa.domain.firmas

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.SesionAutenticada
import java.math.BigDecimal
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class FirmaCoordinatorTest {
    private val gateway = GatewayFirmaFalso()
    private val coordinador = FirmaCoordinator(gateway, SesionFalsa())

    @Test
    fun presentaContratoEnviaOtpYEmitePolizaConLaHuellaPresentada() = runBlocking {
        coordinador.presentar("COT-1")
        coordinador.solicitarCodigo("COT-1")
        coordinador.firmar("COT-1", "123456")

        assertEquals("123456", gateway.codigoFirmado)
        assertEquals(gateway.proceso.huellaDocumento, gateway.huellaFirmada)
        assertEquals("POL-1", coordinador.estado.proceso?.polizaId)
        assertNull(coordinador.estado.error)
    }

    @Test
    fun noEnviaUnaFirmaConCodigoIncompleto() = runBlocking {
        coordinador.presentar("COT-1")
        coordinador.firmar("COT-1", "123")

        assertNull(gateway.codigoFirmado)
        assertEquals(MensajesFirma.CODIGO_INVALIDO, coordinador.estado.error)
    }
}

private class GatewayFirmaFalso : FirmasGateway {
    val proceso = ProcesoFirma(
        cotizacionId = "COT-1",
        estado = "PRESENTADA",
        contrato = ContratoFirma(
            nombreRamo = "Seguro de viaje",
            coberturaPrincipal = "Asistencia integral",
            sumaAsegurada = BigDecimal("20000000"),
            primaTotal = BigDecimal("84000"),
            moneda = "COP",
            clausulas = listOf("Condición"),
            exclusionesPrincipales = emptyList()
        ),
        huellaDocumento = "a".repeat(64),
        otpDestino = null,
        polizaId = null
    )
    var codigoFirmado: String? = null
    var huellaFirmada: String? = null

    override suspend fun presentar(accessToken: String, cotizacionId: String) = ResultadoApi.Exito(proceso)
    override suspend fun solicitarOtp(accessToken: String, cotizacionId: String) =
        ResultadoApi.Exito(proceso.copy(estado = "OTP_ENVIADO", otpDestino = "*** *** 3692"))

    override suspend fun firmar(
        accessToken: String,
        cotizacionId: String,
        codigo: String,
        huellaDocumento: String
    ): ResultadoApi<ProcesoFirma> {
        codigoFirmado = codigo
        huellaFirmada = huellaDocumento
        return ResultadoApi.Exito(proceso.copy(estado = "FIRMADA", polizaId = "POL-1"))
    }
}

private class SesionFalsa : SesionAutenticada {
    override fun accessTokenVigente(): String? = "access-1"
    override fun sesionRechazada() = Unit
}
