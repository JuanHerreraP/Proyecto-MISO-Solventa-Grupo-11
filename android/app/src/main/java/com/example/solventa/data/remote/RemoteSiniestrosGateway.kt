package com.example.solventa.data.remote

import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.siniestros.CODIGO_ARCHIVO_LOCAL_AUSENTE
import com.example.solventa.domain.siniestros.EvidenciaLocal
import com.example.solventa.domain.siniestros.EvidenciaRegistrada
import com.example.solventa.domain.siniestros.Siniestro
import com.example.solventa.domain.siniestros.Siniestros
import com.example.solventa.domain.siniestros.SiniestrosGateway
import com.example.solventa.domain.siniestros.SolicitudSiniestro
import com.example.solventa.domain.siniestros.SolicitudSiniestroAsistido
import com.google.gson.JsonParseException
import com.google.gson.stream.MalformedJsonException
import java.io.File
import java.io.IOException
import java.util.Locale
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.Response

class RemoteSiniestrosGateway(private val api: SiniestrosApi) : SiniestrosGateway {

    override suspend fun listar(accessToken: String): ResultadoApi<Siniestros> =
        llamar({ api.listar(bearer(accessToken)) }) { it.aSiniestros() }

    override suspend fun registrar(
        accessToken: String,
        solicitud: SolicitudSiniestro
    ): ResultadoApi<Siniestro> =
        llamar({
            api.registrar(bearer(accessToken), solicitud.aDto(), solicitud.claveIdempotencia)
        }) { it.aSiniestro() }

    override suspend fun registrarAsistido(
        accessToken: String,
        solicitud: SolicitudSiniestroAsistido
    ): ResultadoApi<Siniestro> =
        llamar({ api.registrarAsistido(bearer(accessToken), solicitud.aDto()) }) { it.aSiniestro() }

    override suspend fun listarDeCliente(
        accessToken: String,
        clienteId: String
    ): ResultadoApi<Siniestros> =
        llamar({ api.listarDeCliente(bearer(accessToken), clienteId) }) { it.aSiniestros() }

    override suspend fun subirEvidencia(
        accessToken: String,
        siniestroId: String,
        evidencia: EvidenciaLocal
    ): ResultadoApi<EvidenciaRegistrada> {
        val archivo = File(evidencia.rutaArchivo)
        if (!archivo.isFile) {
            return ResultadoApi.Fallo(CUERPO_INVALIDO, CODIGO_ARCHIVO_LOCAL_AUSENTE, null)
        }
        val parte = MultipartBody.Part.createFormData(
            "archivo",
            evidencia.nombreArchivo ?: archivo.name,
            archivo.asRequestBody(evidencia.tipoContenido.toMediaTypeOrNull())
        )
        val ubicacion = evidencia.ubicacion
        return llamar({
            api.subirEvidencia(
                autorizacion = bearer(accessToken),
                huella = evidencia.huellaSha256,
                siniestroId = siniestroId,
                archivo = parte,
                capturadaEn = evidencia.capturadaEn?.let { texto(it) },
                latitud = ubicacion?.latitud?.let { texto(numero(it)) },
                longitud = ubicacion?.longitud?.let { texto(numero(it)) },
                precisionMetros = ubicacion?.precisionMetros?.let { texto(numero(it.toDouble())) }
            )
        }) { it.aEvidencia() }
    }

    private fun bearer(accessToken: String) = "Bearer $accessToken"

    private fun texto(valor: String): RequestBody = valor.toRequestBody(TEXTO_PLANO)

    /** Punto decimal siempre, sin importar el idioma del teléfono. */
    private fun numero(valor: Double): String = String.format(Locale.US, "%.7f", valor)

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
        // Respondió algo que no es JSON (por ejemplo, la página de un proxy): no es falta de red.
        ResultadoApi.Fallo(CUERPO_INVALIDO, null, null)
    } catch (error: IOException) {
        ResultadoApi.SinConexion
    } catch (error: JsonParseException) {
        ResultadoApi.Fallo(CUERPO_INVALIDO, null, null)
    }

    private companion object {
        /** Código para respuestas que no se pudieron leer; no coincide con ningún HTTP real. */
        const val CUERPO_INVALIDO = 0
        val TEXTO_PLANO = "text/plain".toMediaType()
    }
}
