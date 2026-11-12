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
    var respuestaAsistido: ResultadoApi<Siniestro> = ResultadoApi.Exito(siniestro(id = "SIN-ASIST"))
    val tokensUsados = mutableListOf<String>()
    val solicitudes = mutableListOf<SolicitudSiniestro>()
    val solicitudesAsistidas = mutableListOf<SolicitudSiniestroAsistido>()
    val clientesConsultados = mutableListOf<String>()

    /** HU04: respuesta por id de evidencia; sin entrada, se acepta. */
    val respuestasEvidencia = mutableMapOf<String, ResultadoApi<EvidenciaRegistrada>>()
    val evidenciasSubidas = mutableListOf<Pair<String, String>>()

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

    override suspend fun registrarAsistido(
        accessToken: String,
        solicitud: SolicitudSiniestroAsistido
    ): ResultadoApi<Siniestro> {
        tokensUsados += accessToken
        solicitudesAsistidas += solicitud
        return respuestaAsistido
    }

    override suspend fun listarDeCliente(
        accessToken: String,
        clienteId: String
    ): ResultadoApi<Siniestros> {
        tokensUsados += accessToken
        clientesConsultados += clienteId
        return respuesta
    }

    override suspend fun subirEvidencia(
        accessToken: String,
        siniestroId: String,
        evidencia: EvidenciaLocal
    ): ResultadoApi<EvidenciaRegistrada> {
        tokensUsados += accessToken
        evidenciasSubidas += siniestroId to evidencia.id
        return respuestasEvidencia[evidencia.id]
            ?: ResultadoApi.Exito(
                EvidenciaRegistrada("EVI-${evidencia.id}", evidencia.huellaSha256, evidencia.geoetiquetada)
            )
    }
}

/** HU04: evidencia local de prueba. */
fun evidencia(
    id: String = "E1",
    tipoContenido: String = "image/jpeg",
    tamano: Long = 2048,
    ubicacion: Ubicacion? = Ubicacion(4.7016, -74.1469, 12f),
    subida: Boolean = false
) = EvidenciaLocal(
    id = id,
    rutaArchivo = "/datos/borradores_siniestro/abc/evidencias/$id.jpg",
    tipoContenido = tipoContenido,
    tipo = ReglasEvidencia.tipoDe(tipoContenido) ?: TipoEvidencia.FOTO,
    tamanoBytes = tamano,
    huellaSha256 = "a".repeat(64),
    capturadaEn = "2026-11-10T15:00:00Z",
    ubicacion = ubicacion,
    subida = subida
)

/** HU04: borradores en memoria, por usuario. */
class BorradoresFalsos : BorradoresSiniestro {
    val porUsuario = mutableMapOf<String, BorradorSiniestro>()
    val archivosEliminados = mutableListOf<String>()
    var guardados = 0

    override suspend fun leer(usuarioId: String): BorradorSiniestro? = porUsuario[usuarioId]

    override suspend fun guardar(usuarioId: String, borrador: BorradorSiniestro) {
        guardados++
        porUsuario[usuarioId] = borrador
    }

    override suspend fun eliminar(usuarioId: String) {
        porUsuario.remove(usuarioId)?.evidencias?.forEach { archivosEliminados += it.id }
    }

    override suspend fun eliminarArchivo(evidencia: EvidenciaLocal) {
        archivosEliminados += evidencia.id
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
