package com.example.solventa.domain.asesor

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.Billetera
import com.example.solventa.domain.polizas.EstadoPoliza
import com.example.solventa.domain.polizas.PolizaResumen
import com.example.solventa.domain.polizas.SesionAutenticada

fun cliente(
    id: String = "CLI-1",
    nombre: String = "Ana",
    apellido: String = "Pérez",
    email: String = "ana@gmail.com"
) = ClienteDeAsesor(clienteId = id, nombre = nombre, apellido = apellido, email = email)

fun billeteraDe(vararg polizas: PolizaResumen) = Billetera(
    polizas = polizas.toList(),
    totalVigentes = polizas.count { it.activa },
    totalInactivas = polizas.count { !it.activa }
)

fun polizaVigente(id: String = "POL-1") = PolizaResumen(
    polizaId = id,
    numeroPoliza = "SOL-VJ-0001",
    ramo = "VIAJE",
    nombreRamo = "Seguro de viaje",
    estado = EstadoPoliza.VIGENTE,
    activa = true,
    fechaInicio = "2026-10-01",
    fechaFin = "2026-12-31",
    coberturaPrincipal = "Asistencia médica en viaje",
    emitidaEn = "2026-09-30T14:00:00Z"
)

fun nuevoAsesor() = DatosNuevoAsesor(
    nombre = "María",
    apellido = "Torres",
    email = "maria@solventa.com",
    password = "Password123!",
    tipoDocumento = "CC",
    numeroDocumento = "1012345678",
    fechaNacimiento = "1990-01-01"
)

fun nuevoAnalista() = DatosNuevoAnalista(
    nombre = "Laura",
    apellido = "Gómez",
    email = "laura@solventa.com",
    password = "Password123!",
    tipoDocumento = "CC",
    numeroDocumento = "1020304050",
    fechaNacimiento = "1992-05-10"
)

class AsesorGatewayFalso : AsesorGateway {
    var respuestaClientes: ResultadoApi<List<ClienteDeAsesor>> = ResultadoApi.Exito(listOf(cliente()))
    var respuestaAsociar: ResultadoApi<ClienteDeAsesor> = ResultadoApi.Exito(cliente(id = "CLI-9"))
    var respuestaPolizas: ResultadoApi<Billetera> = ResultadoApi.Exito(billeteraDe(polizaVigente()))
    var respuestaCrear: ResultadoApi<ClienteDeAsesor> =
        ResultadoApi.Exito(cliente(id = "ASE-NUEVO", nombre = "María", apellido = "Torres"))
    var respuestaCrearAnalista: ResultadoApi<ClienteDeAsesor> =
        ResultadoApi.Exito(cliente(id = "ANA-NUEVO", nombre = "Laura", apellido = "Gómez"))

    val tokensUsados = mutableListOf<String>()
    val correosAsociados = mutableListOf<String>()
    val clientesConsultados = mutableListOf<String>()
    val asesoresCreados = mutableListOf<DatosNuevoAsesor>()
    val analistasCreados = mutableListOf<DatosNuevoAnalista>()

    override suspend fun listarClientes(accessToken: String): ResultadoApi<List<ClienteDeAsesor>> {
        tokensUsados += accessToken
        return respuestaClientes
    }

    override suspend fun asociarCliente(
        accessToken: String,
        email: String
    ): ResultadoApi<ClienteDeAsesor> {
        tokensUsados += accessToken
        correosAsociados += email
        return respuestaAsociar
    }

    override suspend fun polizasDeCliente(
        accessToken: String,
        clienteId: String
    ): ResultadoApi<Billetera> {
        tokensUsados += accessToken
        clientesConsultados += clienteId
        return respuestaPolizas
    }

    override suspend fun crearAsesor(
        accessToken: String,
        datos: DatosNuevoAsesor
    ): ResultadoApi<ClienteDeAsesor> {
        tokensUsados += accessToken
        asesoresCreados += datos
        return respuestaCrear
    }

    override suspend fun crearAnalista(
        accessToken: String,
        datos: DatosNuevoAnalista
    ): ResultadoApi<ClienteDeAsesor> {
        tokensUsados += accessToken
        analistasCreados += datos
        return respuestaCrearAnalista
    }
}

class SesionAsesorFalsa(var token: String? = "access-1") : SesionAutenticada {
    var rechazos = 0

    override fun accessTokenVigente(): String? = token

    override fun sesionRechazada() {
        rechazos++
        token = null
    }
}
