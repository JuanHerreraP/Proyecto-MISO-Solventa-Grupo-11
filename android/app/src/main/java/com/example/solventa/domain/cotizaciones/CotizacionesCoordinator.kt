package com.example.solventa.domain.cotizaciones

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.SesionAutenticada

data class EstadoCotizaciones(
    val cargando: Boolean = false,
    val resultado: ResultadoCotizacion? = null,
    val error: String? = null,
    val cargandoListado: Boolean = false,
    val listado: List<ResultadoCotizacion> = emptyList(),
    val errorListado: String? = null
)

object MensajesCotizaciones {
    const val DATOS_INVALIDOS = "Revisa los datos ingresados para calcular la cotización."
    const val RIESGO_NO_ASEGURABLE = "No podemos ofrecer esta cobertura con el perfil actual."
    const val SIN_CONEXION = "No pudimos conectarnos con Solventa. Revisa tu conexión e inténtalo de nuevo."
    const val ERROR_GENERICO = "No pudimos calcular la cotización. Inténtalo de nuevo."
    const val SESION_VENCIDA = "Tu sesión expiró. Vuelve a ingresar."
}

interface CotizacionesGateway {
    suspend fun listar(
        accessToken: String,
        clienteId: String
    ): ResultadoApi<List<ResultadoCotizacion>>

    suspend fun cotizar(
        accessToken: String,
        clienteId: String,
        ramo: RamoCotizacion,
        datosRiesgo: Map<String, Any>
    ): ResultadoApi<ResultadoCotizacion>
}

class CotizacionesCoordinator(
    private val gateway: CotizacionesGateway,
    private val sesion: SesionAutenticada
) {
    var observador: ((EstadoCotizaciones) -> Unit)? = null
        set(value) {
            field = value
            value?.invoke(estado)
        }

    var estado: EstadoCotizaciones = EstadoCotizaciones()
        private set(value) {
            field = value
            observador?.invoke(value)
        }

    private var generacion = 0

    suspend fun listar(clienteId: String) {
        if (estado.cargandoListado) return
        val token = sesion.accessTokenVigente() ?: return rechazada()
        estado = estado.copy(cargandoListado = true, errorListado = null)
        val inicio = generacion
        val respuesta = gateway.listar(token, clienteId)
        if (inicio != generacion) return

        estado = when (respuesta) {
            is ResultadoApi.Exito -> estado.copy(
                cargandoListado = false,
                listado = respuesta.valor,
                errorListado = null
            )
            is ResultadoApi.Fallo -> when (respuesta.http) {
                401 -> return rechazada()
                else -> estado.copy(
                    cargandoListado = false,
                    errorListado = MensajesCotizaciones.ERROR_GENERICO
                )
            }
            ResultadoApi.SinConexion -> estado.copy(
                cargandoListado = false,
                errorListado = MensajesCotizaciones.SIN_CONEXION
            )
        }
    }

    suspend fun cotizar(clienteId: String, ramo: RamoCotizacion, valores: Map<String, String>) {
        if (estado.cargando) return
        val token = sesion.accessTokenVigente() ?: return rechazada()
        val datos = convertirDatos(ramo, valores)
        if (datos == null) {
            estado = EstadoCotizaciones(error = MensajesCotizaciones.DATOS_INVALIDOS)
            return
        }

        estado = estado.copy(cargando = true, resultado = null, error = null)
        val inicio = generacion
        val respuesta = gateway.cotizar(token, clienteId, ramo, datos)
        if (inicio != generacion) return

        estado = when (respuesta) {
            is ResultadoApi.Exito -> estado.copy(
                cargando = false,
                resultado = respuesta.valor,
                error = null,
                listado = listOf(respuesta.valor) +
                    estado.listado.filterNot { it.cotizacionId == respuesta.valor.cotizacionId }
            )
            is ResultadoApi.Fallo -> when (respuesta.http) {
                401 -> return rechazada()
                409 -> estado.copy(
                    cargando = false,
                    error = respuesta.mensaje ?: MensajesCotizaciones.RIESGO_NO_ASEGURABLE
                )
                422 -> estado.copy(
                    cargando = false,
                    error = respuesta.mensaje ?: MensajesCotizaciones.DATOS_INVALIDOS
                )
                else -> estado.copy(
                    cargando = false,
                    error = MensajesCotizaciones.ERROR_GENERICO
                )
            }
            ResultadoApi.SinConexion -> estado.copy(
                cargando = false,
                error = MensajesCotizaciones.SIN_CONEXION
            )
        }
    }

    fun limpiarResultado() {
        if (estado.resultado != null || estado.error != null || estado.cargando) {
            estado = estado.copy(cargando = false, resultado = null, error = null)
        }
    }

    fun limpiar() {
        generacion++
        if (estado != EstadoCotizaciones()) estado = EstadoCotizaciones()
    }

    private fun rechazada() {
        generacion++
        estado = EstadoCotizaciones(error = MensajesCotizaciones.SESION_VENCIDA)
        sesion.sesionRechazada()
    }

    private fun convertirDatos(
        ramo: RamoCotizacion,
        valores: Map<String, String>
    ): Map<String, Any>? {
        val campos = CatalogoCotizaciones.definicion(ramo).campos.associateBy { it.codigo }
        val convertidos = mutableMapOf<String, Any>()
        for ((codigo, valorOriginal) in valores) {
            val campo = campos[codigo] ?: continue
            val valor = valorOriginal.trim()
            if (valor.isEmpty()) continue
            val convertido: Any = when (campo.tipo) {
                TipoCampoCotizacion.ENTERO -> valor.toIntOrNull() ?: return null
                TipoCampoCotizacion.DECIMAL -> valor.toBigDecimalOrNull() ?: return null
                TipoCampoCotizacion.BOOLEANO -> valor.toBooleanStrictOrNull() ?: return null
                TipoCampoCotizacion.TEXTO,
                TipoCampoCotizacion.FECHA,
                TipoCampoCotizacion.OPCION -> valor
            }
            convertidos[codigo] = convertido
        }
        return convertidos
    }
}

