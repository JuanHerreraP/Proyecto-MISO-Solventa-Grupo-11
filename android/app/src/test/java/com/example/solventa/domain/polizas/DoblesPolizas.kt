package com.example.solventa.domain.polizas

import com.example.solventa.domain.auth.ResultadoApi

fun resumen(
    id: String = "POL-1",
    numero: String = "SOL-VJ-0001",
    estado: EstadoPoliza = EstadoPoliza.VIGENTE,
    nombreRamo: String = "Seguro de viaje",
    emitidaEn: String = "2026-09-30T14:00:00Z"
) = PolizaResumen(
    polizaId = id,
    numeroPoliza = numero,
    ramo = "VIAJE",
    nombreRamo = nombreRamo,
    estado = estado,
    activa = estado == EstadoPoliza.VIGENTE,
    fechaInicio = "2026-10-01",
    fechaFin = "2026-12-31",
    coberturaPrincipal = "Asistencia médica en viaje",
    emitidaEn = emitidaEn
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
    descripcionCobertura = "Atención de emergencias cubiertas",
    sumaAsegurada = "40000000.00",
    moneda = "COP",
    contenidoQr = "SOLVENTA|SOL-VJ-0001|a1b2c3d4e5f60718",
    ramo = "VIAJE",
    primaTotal = "84000.00",
    emitidaEn = "2026-09-30T14:00:00Z",
    exclusionesPrincipales = listOf("Viajes contra recomendación médica")
)

fun historialEndosos() = HistorialEndosos(
    listOf(
        EndosoPoliza(
            endosoId = "END-1",
            numero = 1,
            tipo = "MODIFICACION_COBERTURA",
            fechaEfecto = "2026-10-15",
            creadoEn = "2026-10-14T14:00:00Z",
            cambios = listOf(CambioEndoso("COBERTURA", "Aumenta la suma asegurada")),
            huellaDocumento = "b".repeat(64)
        )
    )
)

val ENLACE = EnlaceCompartido(
    url = "https://api.solventa.co/api/v1/certificados-compartidos/abc",
    expiraEn = "2026-10-22T15:00:00Z"
)

class PolizasGatewayFalso : PolizasGateway {
    var respuestaBilletera: ResultadoApi<Billetera> = ResultadoApi.Exito(billeteraDe(resumen()))
    var respuestaCertificado: ResultadoApi<Certificado> = ResultadoApi.Exito(certificado())
    var respuestaCompartir: ResultadoApi<EnlaceCompartido> = ResultadoApi.Exito(ENLACE)
    var respuestaHistorial: ResultadoApi<HistorialEndosos> = ResultadoApi.Exito(HistorialEndosos(emptyList()))
    var respuestaDocumento: ResultadoApi<DocumentoPoliza> = ResultadoApi.Exito(
        DocumentoPoliza("poliza.pdf", "%PDF-prueba".toByteArray(), "a".repeat(64))
    )

    val tokensUsados = mutableListOf<String>()
    val certificadosPedidos = mutableListOf<String>()
    val historialesPedidos = mutableListOf<String>()
    val documentosPedidos = mutableListOf<String>()
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

    override suspend fun historialEndosos(
        accessToken: String,
        polizaId: String
    ): ResultadoApi<HistorialEndosos> {
        tokensUsados += accessToken
        historialesPedidos += polizaId
        return respuestaHistorial
    }

    override suspend fun documento(
        accessToken: String,
        polizaId: String
    ): ResultadoApi<DocumentoPoliza> {
        tokensUsados += accessToken
        documentosPedidos += polizaId
        return respuestaDocumento
    }

    override suspend fun compartir(accessToken: String, polizaId: String): ResultadoApi<EnlaceCompartido> {
        tokensUsados += accessToken
        compartidos += polizaId
        return respuestaCompartir
    }
}

class SesionFalsa(
    var token: String? = "access-1",
    var idUsuario: String? = "u-1"
) : SesionPolizasOffline {
    var rechazos = 0

    override fun usuarioId(): String? = idUsuario

    override fun accessTokenVigente(): String? = token

    override fun sesionRechazada() {
        rechazos++
        token = null
    }
}

class CachePolizasFalsa : CachePolizas {
    private data class Instantanea(
        val billetera: Billetera,
        val certificados: List<Certificado>,
        val historiales: Map<String, HistorialEndosos>,
        val sincronizadaEnMs: Long
    )

    private val datos = mutableMapOf<ClaveUsuarioCache, Instantanea>()

    override suspend fun reemplazar(
        usuario: ClaveUsuarioCache,
        billetera: Billetera,
        certificados: List<Certificado>,
        sincronizadaEnMs: Long
    ) {
        val polizas = billetera.polizas.mapTo(mutableSetOf()) { it.polizaId }
        val historiales = datos[usuario]?.historiales.orEmpty().filterKeys { it in polizas }
        datos[usuario] = Instantanea(billetera, certificados, historiales, sincronizadaEnMs)
    }

    override suspend fun billetera(usuario: ClaveUsuarioCache): BilleteraCacheada? =
        datos[usuario]?.let {
            BilleteraCacheada(it.billetera, MetadatosSincronizacion(usuario, it.sincronizadaEnMs))
        }

    override suspend fun historialEndosos(
        usuario: ClaveUsuarioCache,
        polizaId: String
    ): HistorialEndososCacheado? = datos[usuario]?.let { instantanea ->
        instantanea.historiales[polizaId]?.let {
            HistorialEndososCacheado(
                it,
                MetadatosSincronizacion(usuario, instantanea.sincronizadaEnMs)
            )
        }
    }

    override suspend fun guardarHistorialEndosos(
        usuario: ClaveUsuarioCache,
        polizaId: String,
        historial: HistorialEndosos
    ) {
        val instantanea = datos[usuario] ?: return
        require(instantanea.billetera.polizas.any { it.polizaId == polizaId })
        datos[usuario] = instantanea.copy(
            historiales = instantanea.historiales + (polizaId to historial)
        )
    }

    override suspend fun certificado(
        usuario: ClaveUsuarioCache,
        polizaId: String
    ): CertificadoCacheado? = datos[usuario]
        ?.let { instantanea ->
            instantanea.certificados.firstOrNull { it.polizaId == polizaId }
                ?.let {
                    CertificadoCacheado(
                        it,
                        MetadatosSincronizacion(usuario, instantanea.sincronizadaEnMs)
                    )
                }
        }

    override suspend fun eliminar(usuario: ClaveUsuarioCache) {
        datos.remove(usuario)
    }

    override suspend fun eliminarTodo() {
        datos.clear()
    }
}
