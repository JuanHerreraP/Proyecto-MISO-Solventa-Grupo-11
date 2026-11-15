package com.example.solventa.domain.asistencias

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.SesionAutenticada
import com.example.solventa.domain.siniestros.Ubicacion

val BOGOTA = Ubicacion(4.7110, -74.0721)

fun servicioAsistencia(
    codigo: TipoServicio = TipoServicio.REPARACION_DISPOSITIVO
) = ServicioAsistencia(codigo = codigo, nombre = codigo.etiqueta)

fun prestadorCercano(
    id: String = "PREST-TEC-001",
    nombre: String = "Solventa Tech Centro",
    tipo: TipoServicio = TipoServicio.REPARACION_DISPOSITIVO,
    distancia: Double = 0.5
) = PrestadorCercano(
    prestadorId = id,
    nombre = nombre,
    tipoServicio = tipo,
    direccion = "Dirección de demostración",
    telefono = "3000000001",
    latitud = 4.7150,
    longitud = -74.0690,
    distanciaKm = distancia
)

fun asistencia(
    id: String = "ASI-1",
    estado: EstadoAsistencia = EstadoAsistencia.SOLICITADA,
    servicio: TipoServicio = TipoServicio.REPARACION_DISPOSITIVO
) = Asistencia(
    asistenciaId = id,
    polizaId = "POL-1",
    prestador = PrestadorResumen("PREST-TEC-001", "Solventa Tech Centro", "3000000001"),
    servicio = servicio,
    estado = estado,
    latitud = 4.7110,
    longitud = -74.0721,
    observaciones = null,
    creadaEn = "2026-11-15T14:30:00Z",
    canceladaEn = if (estado == EstadoAsistencia.CANCELADA) "2026-11-15T15:00:00Z" else null
)

/** Gateway falso configurable por respuesta (patrón de DoblesSiniestros). */
class AsistenciasGatewayFalso : AsistenciasGateway {
    var respuestaServicios: ResultadoApi<ServiciosPoliza> =
        ResultadoApi.Exito(
            ServiciosPoliza(
                polizaId = "POL-1",
                ramo = "PROTECCION_DISPOSITIVOS",
                servicios = listOf(
                    servicioAsistencia(TipoServicio.DIAGNOSTICO_TECNICO),
                    servicioAsistencia(TipoServicio.REPARACION_DISPOSITIVO)
                )
            )
        )
    var respuestaCercanos: ResultadoApi<PrestadoresCercanos> =
        ResultadoApi.Exito(
            PrestadoresCercanos(
                polizaId = "POL-1",
                servicio = TipoServicio.REPARACION_DISPOSITIVO,
                latitud = 4.7110,
                longitud = -74.0721,
                prestadores = listOf(
                    prestadorCercano("PREST-TEC-001", distancia = 0.5),
                    prestadorCercano("PREST-TEC-002", "TechCare Norte", distancia = 1.8)
                )
            )
        )
    var respuestaSolicitar: ResultadoApi<Asistencia> = ResultadoApi.Exito(asistencia())
    var respuestaListar: ResultadoApi<List<Asistencia>> = ResultadoApi.Exito(listOf(asistencia()))
    var respuestaCancelar: ResultadoApi<Asistencia> =
        ResultadoApi.Exito(asistencia(estado = EstadoAsistencia.CANCELADA))

    val tokensUsados = mutableListOf<String>()
    val solicitudes = mutableListOf<NuevaAsistencia>()
    val canceladas = mutableListOf<String>()
    var ultimoRadioKm: Double? = null

    override suspend fun servicios(accessToken: String, polizaId: String): ResultadoApi<ServiciosPoliza> {
        tokensUsados += accessToken
        return respuestaServicios
    }

    override suspend fun prestadoresCercanos(
        accessToken: String,
        polizaId: String,
        servicio: TipoServicio,
        latitud: Double,
        longitud: Double,
        radioKm: Double
    ): ResultadoApi<PrestadoresCercanos> {
        tokensUsados += accessToken
        ultimoRadioKm = radioKm
        return respuestaCercanos
    }

    override suspend fun solicitar(
        accessToken: String,
        solicitud: NuevaAsistencia
    ): ResultadoApi<Asistencia> {
        tokensUsados += accessToken
        solicitudes += solicitud
        return respuestaSolicitar
    }

    override suspend fun listar(accessToken: String): ResultadoApi<List<Asistencia>> {
        tokensUsados += accessToken
        return respuestaListar
    }

    override suspend fun cancelar(accessToken: String, asistenciaId: String): ResultadoApi<Asistencia> {
        tokensUsados += accessToken
        canceladas += asistenciaId
        return respuestaCancelar
    }
}

class SesionAsistenciasFalsa(var token: String? = "access-1") : SesionAutenticada {
    var rechazos = 0

    override fun accessTokenVigente(): String? = token

    override fun sesionRechazada() {
        rechazos++
        token = null
    }
}
