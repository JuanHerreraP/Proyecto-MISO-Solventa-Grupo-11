package com.example.solventa.data.remote

import com.example.solventa.domain.auth.DatosRegistro
import com.google.gson.Gson
import com.google.gson.JsonParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SolicitudRegistroDtoTest {
    @Test
    fun serializaTodosLosCamposEsperadosPorElBackend() {
        val datos = DatosRegistro(
            nombre = "Ana",
            apellido = "Perez",
            email = "ana@example.com",
            password = "Password123!",
            tipoDocumento = "CC",
            numeroDocumento = "123456789",
            fechaNacimiento = "1999-01-01",
            celular = "3001234567",
            selfieBase64 = "/9j/2Q=="
        )

        val payload = JsonParser.parseString(
            Gson().toJson(SolicitudRegistroDto.desde(datos))
        ).asJsonObject

        assertEquals("Ana", payload.get("nombre").asString)
        assertEquals("Perez", payload.get("apellido").asString)
        assertEquals("CC", payload.get("tipo_documento").asString)
        assertEquals("123456789", payload.get("numero_documento").asString)
        assertEquals("1999-01-01", payload.get("fecha_nacimiento").asString)
        assertEquals("3001234567", payload.get("celular").asString)
        assertTrue(payload.get("acepta_validacion_identidad").asBoolean)
        assertEquals("/9j/2Q==", payload.get("selfie_base64").asString)
    }

    @Test
    fun serializaErroresDeValidacionDelBackend() {
        val (codigo, mensaje) = RemoteAuthGateway.leerError(
            """{"detail":[{"loc":["body","email"],"msg":"value is not a valid email"}]}"""
        )

        assertEquals(null, codigo)
        assertEquals("value is not a valid email", mensaje)
    }
}
