package com.example.solventa.data.remote

import com.example.solventa.domain.auth.Perfil
import com.example.solventa.domain.auth.RegistroCreado
import com.example.solventa.domain.auth.Tokens
import com.google.gson.Gson
import com.google.gson.JsonParser
import org.junit.Assert.assertEquals
import org.junit.Test

class AuthDtosTest {
    private val gson = Gson()

    @Test
    fun tokensDelBackendSeConviertenAlModeloDeDominio() {
        val dto = gson.fromJson(
            """{"access_token":"a","refresh_token":"r","token_type":"bearer","expires_in":60,"refresh_expires_in":120}""",
            RespuestaTokensDto::class.java
        )

        assertEquals(Tokens("a", "r", 60), dto.aTokens())
        assertEquals("bearer", dto.tokenType)
        assertEquals(120, dto.refreshExpiresIn)
    }

    @Test
    fun perfilDelBackendSeConvierteAlModeloDeDominio() {
        val dto = gson.fromJson(
            """{"id":"u-1","nombre":"Ana","apellido":"Pérez","email":"ana@gmail.com","rol":"CLIENTE"}""",
            PerfilDto::class.java
        )

        assertEquals(Perfil("u-1", "Ana", "Pérez", "ana@gmail.com", "CLIENTE"), dto.aPerfil())
    }

    @Test
    fun respuestaDeRegistroSeConvierteAlModeloDeDominio() {
        val dto = gson.fromJson("""{"email":"ana@gmail.com","kyc_validado":false}""", RespuestaRegistroDto::class.java)

        assertEquals(RegistroCreado("ana@gmail.com", false), dto.aRegistroCreado())
    }

    @Test
    fun solicitudesUsanLosNombresDeCampoDelBackend() {
        val login = JsonParser.parseString(gson.toJson(SolicitudLoginDto("ana@gmail.com", "x"))).asJsonObject
        val refresh = JsonParser.parseString(gson.toJson(SolicitudRefreshDto("r"))).asJsonObject

        assertEquals(setOf("email", "password"), login.keySet())
        assertEquals("r", refresh.get("refresh_token").asString)
    }
}
