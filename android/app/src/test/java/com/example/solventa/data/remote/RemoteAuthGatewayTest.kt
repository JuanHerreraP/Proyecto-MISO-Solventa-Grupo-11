package com.example.solventa.data.remote

import com.example.solventa.domain.auth.DatosRegistro
import com.example.solventa.domain.auth.Perfil
import com.example.solventa.domain.auth.RegistroCreado
import com.example.solventa.domain.auth.ResultadoApi
import com.example.solventa.domain.auth.Tokens
import com.google.gson.JsonParser
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

/** Prueba el gateway contra un servidor HTTP falso, con Retrofit y Gson reales. */
class RemoteAuthGatewayTest {
    private lateinit var servidor: MockWebServer
    private lateinit var gateway: RemoteAuthGateway

    private val datos = DatosRegistro(
        nombre = "Ana",
        apellido = "Perez",
        email = "ana@gmail.com",
        password = "Password123!",
        tipoDocumento = "CC",
        numeroDocumento = "1000000001",
        fechaNacimiento = "1999-01-01",
        celular = "3001234567",
        selfieBase64 = "/9j/2Q=="
    )

    private val tokensJson = """
        {"access_token":"access-1","refresh_token":"refresh-1","token_type":"bearer",
         "expires_in":1800,"refresh_expires_in":604800}
    """.trimIndent()

    @Before
    fun iniciar() {
        servidor = MockWebServer()
        servidor.start()
        gateway = RemoteAuthGateway(ApiClient.crearAuthApi(servidor.url("/").toString()))
    }

    @After
    fun detener() {
        try {
            servidor.shutdown()
        } catch (ignorado: Exception) {
            // Algunas pruebas ya lo apagaron para simular falta de conexión.
        }
    }

    private fun responder(codigo: Int, cuerpo: String = "") {
        servidor.enqueue(
            MockResponse()
                .setResponseCode(codigo)
                .setHeader("Content-Type", "application/json")
                .setBody(cuerpo)
        )
    }

    // --- Login ---

    @Test
    fun loginExitosoDevuelveLosTokens() = runBlocking {
        responder(200, tokensJson)

        val resultado = gateway.login("ana@gmail.com", "clave")

        assertEquals(ResultadoApi.Exito(Tokens("access-1", "refresh-1", 1800)), resultado)
        val peticion = servidor.takeRequest()
        assertEquals("POST", peticion.method)
        assertEquals("/api/v1/auth/login", peticion.path)
        val cuerpo = JsonParser.parseString(peticion.body.readUtf8()).asJsonObject
        assertEquals("ana@gmail.com", cuerpo.get("email").asString)
        assertEquals("clave", cuerpo.get("password").asString)
    }

    @Test
    fun loginRechazadoDevuelveCodigoYMensajeDelBackend() = runBlocking {
        responder(401, """{"detail":{"codigo":"INVALID_CREDENTIALS","mensaje":"Credenciales inválidas"}}""")

        val resultado = gateway.login("ana@gmail.com", "mala")

        assertEquals(ResultadoApi.Fallo(401, "INVALID_CREDENTIALS", "Credenciales inválidas"), resultado)
    }

    @Test
    fun respuestaExitosaSinCuerpoSeTrataComoFallo() = runBlocking {
        responder(204)

        val resultado = gateway.login("ana@gmail.com", "clave")

        assertEquals(ResultadoApi.Fallo(204, null, null), resultado)
    }

    @Test
    fun sinServidorDevuelveSinConexion() = runBlocking {
        servidor.shutdown()

        assertEquals(ResultadoApi.SinConexion, gateway.login("ana@gmail.com", "clave"))
        assertEquals(ResultadoApi.SinConexion, gateway.renovar("refresh-1"))
        assertEquals(ResultadoApi.SinConexion, gateway.cerrarSesion("refresh-1"))
        assertEquals(ResultadoApi.SinConexion, gateway.perfil("access-1"))
        assertEquals(ResultadoApi.SinConexion, gateway.registrar(datos))
    }

    // --- Renovación, cierre y perfil ---

    @Test
    fun renovarEnviaElRefreshTokenYDevuelveElParNuevo() = runBlocking {
        responder(200, tokensJson)

        val resultado = gateway.renovar("refresh-0")

        assertEquals(ResultadoApi.Exito(Tokens("access-1", "refresh-1", 1800)), resultado)
        val peticion = servidor.takeRequest()
        assertEquals("/api/v1/auth/refresh", peticion.path)
        assertEquals(
            "refresh-0",
            JsonParser.parseString(peticion.body.readUtf8()).asJsonObject.get("refresh_token").asString
        )
    }

    @Test
    fun cerrarSesionExitosoDevuelveExito() = runBlocking {
        responder(204)

        assertEquals(ResultadoApi.Exito(Unit), gateway.cerrarSesion("refresh-1"))
        assertEquals("/api/v1/auth/logout", servidor.takeRequest().path)
    }

    @Test
    fun cerrarSesionConErrorDevuelveFallo() = runBlocking {
        responder(500, """{"detail":"Error interno"}""")

        assertEquals(ResultadoApi.Fallo(500, null, "Error interno"), gateway.cerrarSesion("refresh-1"))
    }

    @Test
    fun perfilEnviaElAccessTokenComoBearer() = runBlocking {
        responder(
            200,
            """{"id":"u-1","nombre":"Ana","apellido":"Pérez","email":"ana@gmail.com","rol":"CLIENTE"}"""
        )

        val resultado = gateway.perfil("access-1")

        assertEquals(ResultadoApi.Exito(Perfil("u-1", "Ana", "Pérez", "ana@gmail.com", "CLIENTE")), resultado)
        val peticion = servidor.takeRequest()
        assertEquals("/api/v1/auth/me", peticion.path)
        assertEquals("Bearer access-1", peticion.getHeader("Authorization"))
    }

    // --- Registro ---

    @Test
    fun registroCreadoDevuelveElResultadoDelKyc() = runBlocking {
        responder(201, """{"email":"ana@gmail.com","kyc_validado":true}""")

        val resultado = gateway.registrar(datos)

        assertEquals(ResultadoApi.Exito(RegistroCreado("ana@gmail.com", true)), resultado)
        assertEquals("/api/v1/auth/register", servidor.takeRequest().path)
    }

    @Test
    fun registroPendienteDevuelveFalloConCodigo202() = runBlocking {
        responder(202, """{"detail":{"codigo":"KYC_PENDING","mensaje":"Pendiente"}}""")

        assertEquals(ResultadoApi.Fallo(202, "KYC_PENDING", "Pendiente"), gateway.registrar(datos))
    }

    @Test
    fun registroRechazadoDevuelveElMensajeDelBackend() = runBlocking {
        responder(409, """{"detail":"El correo ya está registrado."}""")

        assertEquals(ResultadoApi.Fallo(409, null, "El correo ya está registrado."), gateway.registrar(datos))
    }

    @Test
    fun registroConErrorSinCuerpoDevuelveFalloSinMensaje() = runBlocking {
        responder(500)

        assertEquals(ResultadoApi.Fallo(500, null, null), gateway.registrar(datos))
    }

    // --- Lectura de errores ---

    @Test
    fun leerErrorIgnoraCuerposVaciosOInesperados() {
        assertEquals(null to null, RemoteAuthGateway.leerError(null))
        assertEquals(null to null, RemoteAuthGateway.leerError("   "))
        assertEquals(null to null, RemoteAuthGateway.leerError("no es json"))
        assertEquals(null to null, RemoteAuthGateway.leerError("[1,2]"))
        assertEquals(null to null, RemoteAuthGateway.leerError("""{"otro":"campo"}"""))
        assertEquals(null to null, RemoteAuthGateway.leerError("""{"detail":null}"""))
    }

    @Test
    fun leerErrorAceptaDetalleComoTextoObjetoOLista() {
        assertEquals(null to "Mensaje", RemoteAuthGateway.leerError("""{"detail":"Mensaje"}"""))
        assertEquals(
            "CODIGO" to "Mensaje",
            RemoteAuthGateway.leerError("""{"detail":{"codigo":"CODIGO","mensaje":"Mensaje"}}""")
        )
        assertEquals(
            null to null,
            RemoteAuthGateway.leerError("""{"detail":{"codigo":{"x":1},"mensaje":[1]}}""")
        )
        assertEquals(
            null to "primero",
            RemoteAuthGateway.leerError("""{"detail":[1,{"loc":["body"]},{"msg":"primero"},{"msg":"segundo"}]}""")
        )
        assertNull(RemoteAuthGateway.leerError("""{"detail":[]}""").second)
    }
}
