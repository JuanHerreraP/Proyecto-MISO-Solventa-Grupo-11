package com.example.solventa.domain.asesor

import com.example.solventa.domain.auth.ResultadoApi
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** HU20: reglas del asesor de ventas (clientes, asociación, pólizas y alta), sin Android. */
class AsesorCoordinatorTest {

    @Test
    fun cargarClientesEnviaElTokenYGuardaLaLista() = runBlocking {
        val gateway = AsesorGatewayFalso()
        gateway.respuestaClientes = ResultadoApi.Exito(
            listOf(cliente(id = "CLI-1", nombre = "Ana"), cliente(id = "CLI-2", nombre = "Luis"))
        )
        val coordinador = AsesorCoordinator(gateway, SesionAsesorFalsa(token = "access-9"))

        coordinador.cargarClientes()

        val estado = coordinador.estado
        assertEquals(listOf("CLI-1", "CLI-2"), estado.clientes.map { it.clienteId })
        assertNull(estado.error)
        assertEquals(listOf("access-9"), gateway.tokensUsados)
    }

    @Test
    fun errorAlCargarClientes() = runBlocking {
        val gateway = AsesorGatewayFalso()
        gateway.respuestaClientes = ResultadoApi.Fallo(500, null, null)
        val coordinador = AsesorCoordinator(gateway, SesionAsesorFalsa())

        coordinador.cargarClientes()

        assertEquals(MensajesAsesor.ERROR_CLIENTES, coordinador.estado.error)
    }

    @Test
    fun asociarClienteAgregaLaListaYAvisa() = runBlocking {
        val gateway = AsesorGatewayFalso()
        gateway.respuestaClientes = ResultadoApi.Exito(emptyList())
        gateway.respuestaAsociar = ResultadoApi.Exito(cliente(id = "CLI-9", nombre = "Zoe"))
        val coordinador = AsesorCoordinator(gateway, SesionAsesorFalsa())
        coordinador.cargarClientes()

        coordinador.asociarCliente("zoe@gmail.com")

        val estado = coordinador.estado
        assertEquals("CLI-9", estado.clienteAsociado?.clienteId)
        assertTrue(estado.clientes.any { it.clienteId == "CLI-9" })
        assertEquals(listOf("zoe@gmail.com"), gateway.correosAsociados)
    }

    @Test
    fun asociarClienteInexistenteTraduceElCodigo() = runBlocking {
        val gateway = AsesorGatewayFalso()
        gateway.respuestaAsociar = ResultadoApi.Fallo(404, "CLIENTE_NO_ENCONTRADO", null)
        val coordinador = AsesorCoordinator(gateway, SesionAsesorFalsa())

        coordinador.asociarCliente("nadie@gmail.com")

        assertEquals(MensajesAsesor.CLIENTE_NO_ENCONTRADO, coordinador.estado.errorAsociar)
    }

    @Test
    fun asociarClienteYaAsociadoTraduceElCodigo() = runBlocking {
        val gateway = AsesorGatewayFalso()
        gateway.respuestaAsociar = ResultadoApi.Fallo(409, "CLIENTE_YA_ASOCIADO", null)
        val coordinador = AsesorCoordinator(gateway, SesionAsesorFalsa())

        coordinador.asociarCliente("ana@gmail.com")

        assertEquals(MensajesAsesor.CLIENTE_YA_ASOCIADO, coordinador.estado.errorAsociar)
    }

    @Test
    fun seleccionarClienteCargaSusPolizas() = runBlocking {
        val gateway = AsesorGatewayFalso()
        gateway.respuestaPolizas = ResultadoApi.Exito(billeteraDe(polizaVigente("POL-7")))
        val coordinador = AsesorCoordinator(gateway, SesionAsesorFalsa())

        coordinador.seleccionarCliente(cliente(id = "CLI-5"))

        val estado = coordinador.estado
        assertEquals("CLI-5", estado.clienteSeleccionado?.clienteId)
        assertEquals(listOf("CLI-5"), gateway.clientesConsultados)
        assertEquals(1, estado.polizasCliente?.vigentes?.size)
        assertNull(estado.errorPolizas)
    }

    @Test
    fun crearAsesorEnviaLosDatosYMarcaCreado() = runBlocking {
        val gateway = AsesorGatewayFalso()
        val coordinador = AsesorCoordinator(gateway, SesionAsesorFalsa())

        coordinador.crearAsesor(nuevoAsesor())

        val estado = coordinador.estado
        assertEquals("María", estado.asesorCreado?.nombre)
        assertEquals(1, gateway.asesoresCreados.size)
        assertEquals("maria@solventa.com", gateway.asesoresCreados.first().email)
    }

    @Test
    fun crearAsesorConCorreoDuplicadoTraduceElCodigo() = runBlocking {
        val gateway = AsesorGatewayFalso()
        gateway.respuestaCrear = ResultadoApi.Fallo(409, "EMAIL_ALREADY_EXISTS", null)
        val coordinador = AsesorCoordinator(gateway, SesionAsesorFalsa())

        coordinador.crearAsesor(nuevoAsesor())

        assertEquals(MensajesAsesor.EMAIL_YA_EXISTE, coordinador.estado.errorCrearAsesor)
    }

    @Test
    fun token401CierraLaSesion() = runBlocking {
        val gateway = AsesorGatewayFalso()
        gateway.respuestaClientes = ResultadoApi.Fallo(401, "TOKEN_EXPIRED", null)
        val sesion = SesionAsesorFalsa(token = "viejo")
        val coordinador = AsesorCoordinator(gateway, sesion)

        coordinador.cargarClientes()

        assertEquals(1, sesion.rechazos)
        assertEquals(MensajesAsesor.SESION_VENCIDA, coordinador.estado.error)
    }

    @Test
    fun limpiarRestableceElEstado() = runBlocking {
        val gateway = AsesorGatewayFalso()
        val coordinador = AsesorCoordinator(gateway, SesionAsesorFalsa())
        coordinador.cargarClientes()

        coordinador.limpiar()

        assertEquals(EstadoAsesor(), coordinador.estado)
    }
}
