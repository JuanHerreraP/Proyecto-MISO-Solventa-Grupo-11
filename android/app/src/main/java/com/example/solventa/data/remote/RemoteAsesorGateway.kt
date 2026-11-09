package com.example.solventa.data.remote

import com.example.solventa.domain.asesor.AsesorGateway
import com.example.solventa.domain.asesor.ClienteDeAsesor
import com.example.solventa.domain.asesor.DatosNuevoAsesor
import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.polizas.Billetera
import com.google.gson.JsonParseException
import com.google.gson.stream.MalformedJsonException
import java.io.IOException
import retrofit2.Response

class RemoteAsesorGateway(private val api: AsesorApi) : AsesorGateway {

    override suspend fun listarClientes(accessToken: String): ResultadoApi<List<ClienteDeAsesor>> =
        llamar({ api.listarClientes(bearer(accessToken)) }) { it.aClientes() }

    override suspend fun asociarCliente(
        accessToken: String,
        email: String
    ): ResultadoApi<ClienteDeAsesor> =
        llamar({ api.asociarCliente(bearer(accessToken), SolicitudAsociarClienteDto(email)) }) {
            it.aCliente()
        }

    override suspend fun polizasDeCliente(
        accessToken: String,
        clienteId: String
    ): ResultadoApi<Billetera> =
        llamar({ api.polizasDeCliente(bearer(accessToken), clienteId) }) { it.aBilletera() }

    override suspend fun crearAsesor(
        accessToken: String,
        datos: DatosNuevoAsesor
    ): ResultadoApi<ClienteDeAsesor> =
        llamar({
            api.crearAsesor(
                bearer(accessToken),
                SolicitudCrearAsesorDto(
                    nombre = datos.nombre,
                    apellido = datos.apellido,
                    email = datos.email,
                    password = datos.password,
                    tipoDocumento = datos.tipoDocumento,
                    numeroDocumento = datos.numeroDocumento,
                    fechaNacimiento = datos.fechaNacimiento
                )
            )
        }) { it.aCliente() }

    private fun bearer(accessToken: String) = "Bearer $accessToken"

    /** Un cuerpo exitoso que no se puede mapear se trata como fallo, sin romper la UI. */
    private suspend fun <D : Any, T : Any> llamar(
        peticion: suspend () -> Response<D>,
        mapear: (D) -> T?
    ): ResultadoApi<T> = try {
        val respuesta = peticion()
        val cuerpo = respuesta.body()
        if (respuesta.isSuccessful) {
            val valor = cuerpo?.let(mapear)
            if (valor != null) ResultadoApi.Exito(valor) else ResultadoApi.Fallo(respuesta.code(), null, null)
        } else {
            val (codigo, mensaje) = RemoteAuthGateway.leerError(respuesta.errorBody()?.string())
            ResultadoApi.Fallo(respuesta.code(), codigo, mensaje)
        }
    } catch (error: MalformedJsonException) {
        ResultadoApi.Fallo(CUERPO_INVALIDO, null, null)
    } catch (error: IOException) {
        ResultadoApi.SinConexion
    } catch (error: JsonParseException) {
        ResultadoApi.Fallo(CUERPO_INVALIDO, null, null)
    }

    private companion object {
        /** Código para respuestas que no se pudieron leer; no coincide con ningún HTTP real. */
        const val CUERPO_INVALIDO = 0
    }
}
