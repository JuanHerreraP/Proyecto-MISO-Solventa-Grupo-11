package com.example.solventa.domain.firmas

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.SesionAutenticada

/** Coordina presentación, OTP y firma del contrato ya pagado. */
class FirmaCoordinator(
    private val gateway: FirmasGateway,
    private val sesion: SesionAutenticada
) {
    var observador: ((EstadoFirma) -> Unit)? = null
        set(value) {
            field = value
            value?.invoke(estado)
        }

    var estado: EstadoFirma = EstadoFirma()
        private set(value) {
            field = value
            observador?.invoke(value)
        }

    private var generacion = 0

    suspend fun presentar(cotizacionId: String) {
        if (estado.cargando || estado.proceso?.cotizacionId == cotizacionId) return
        ejecutar(cargando = { it.copy(cargando = true, error = null) }) { token ->
            gateway.presentar(token, cotizacionId)
        }
    }

    suspend fun solicitarCodigo(cotizacionId: String) {
        if (estado.enviandoCodigo || estado.firmando) return
        ejecutar(cargando = { it.copy(enviandoCodigo = true, error = null) }) { token ->
            gateway.solicitarOtp(token, cotizacionId)
        }
    }

    suspend fun firmar(cotizacionId: String, codigo: String) {
        val proceso = estado.proceso ?: return
        if (!codigo.matches(Regex("\\d{6}"))) {
            estado = estado.copy(error = MensajesFirma.CODIGO_INVALIDO)
            return
        }
        if (estado.firmando) return
        ejecutar(cargando = { it.copy(firmando = true, error = null) }) { token ->
            gateway.firmar(token, cotizacionId, codigo, proceso.huellaDocumento)
        }
    }

    fun limpiar() {
        generacion++
        if (estado != EstadoFirma()) estado = EstadoFirma()
    }

    private suspend fun ejecutar(
        cargando: (EstadoFirma) -> EstadoFirma,
        operacion: suspend (String) -> ResultadoApi<ProcesoFirma>
    ) {
        val token = sesion.accessTokenVigente() ?: return rechazada()
        estado = cargando(estado)
        val inicio = generacion
        when (val respuesta = operacion(token)) {
            is ResultadoApi.Exito -> if (inicio == generacion) {
                estado = estado.copy(cargando = false, enviandoCodigo = false, firmando = false, proceso = respuesta.valor)
            }
            is ResultadoApi.Fallo -> if (inicio == generacion) {
                if (respuesta.http == 401) return rechazada()
                estado = estado.copy(
                    cargando = false,
                    enviandoCodigo = false,
                    firmando = false,
                    error = respuesta.codigo ?: MensajesFirma.ERROR_GENERICO
                )
            }
            ResultadoApi.SinConexion -> if (inicio == generacion) {
                estado = estado.copy(
                    cargando = false,
                    enviandoCodigo = false,
                    firmando = false,
                    error = MensajesFirma.SIN_CONEXION
                )
            }
        }
    }

    private fun rechazada() {
        generacion++
        estado = EstadoFirma(error = MensajesFirma.SESION_VENCIDA)
        sesion.sesionRechazada()
    }
}
