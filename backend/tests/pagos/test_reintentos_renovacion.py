"""Pago de una renovación: rechazo con nuevo intento y reintentos sin doble cobro (HU21).

Cubre los criterios 4 y 5 de la historia con una renovación, que es la prima pendiente de una
póliza: un pago rechazado no cambia nada y se puede volver a intentar, y un reintento por una
interrupción nunca cobra ni registra dos veces una transacción ya confirmada.
"""

from datetime import date

import pytest

from app.pagos.comprobantes import PagoSinComprobante, ServicioComprobantes
from app.pagos.modelos import EstadoPago
from app.pagos.pasarela_simulada import PasarelaSimulada
from app.pagos.puertos import PasarelaNoDisponible
from app.pagos.repositorio_comprobantes import RepositorioComprobantesEnMemoria
from app.pagos.servicio import CotizacionNoPagable, ServicioPagos, en_cadena
from app.polizas.dominio.renovacion import EstadoRenovacion
from app.polizas.primas_pendientes import ServicioPrimasPendientes
from tests.primas_pendientes.fabrica import FirmasFalsas
from tests.renovaciones.fabrica import (
    CLIENTE,
    POLIZA,
    TITULAR,
    Entorno,
    crear_entorno,
    solicitud_pago,
)


class PasarelaContadora(PasarelaSimulada):
    def __init__(self):
        super().__init__(url_base="http://pruebas")
        self.llamadas = 0

    def cobrar(self, solicitud):
        self.llamadas += 1
        return super().cobrar(solicitud)


class Escenario:
    """Una renovación iniciada, con el recaudo completo (pago, renovación y comprobante)."""

    def __init__(self, avisar_pagos: bool = True):
        self.e: Entorno = crear_entorno(avisar_pagos=avisar_pagos)
        self.pasarela = PasarelaContadora()
        self.comprobantes = ServicioComprobantes(
            RepositorioComprobantesEnMemoria(),
            self.e.cotizaciones,
            self.e.renovaciones,
            self.e.polizas,
            reloj=self.e.reloj,
        )
        avisos = (self.e.servicio.aplicar_pago, self.comprobantes.emitir) if avisar_pagos else ()
        self.pagos = ServicioPagos(
            self.e.pagos,
            self.e.cotizaciones,
            self.pasarela,
            reloj=self.e.reloj,
            al_aprobar=en_cadena(*avisos),
        )
        self.renovacion, _ = self.e.servicio.iniciar(TITULAR, POLIZA, "k-1")
        self.firmas = FirmasFalsas()
        self.pendientes = ServicioPrimasPendientes(
            cotizaciones=self.e.cotizaciones,
            pagos=self.e.pagos,
            polizas=self.e.polizas,
            renovaciones=self.e.renovaciones,
            firmas=self.firmas,
            aplicar_pago=self.e.servicio.aplicar_pago,
            reloj=self.e.reloj,
        )

    def pagar(self, llave: str, token: str = "tok_visa_aprobado"):
        return self.pagos.pagar(
            CLIENTE, llave, solicitud_pago(self.renovacion.cotizacion_id, token)
        )

    @property
    def estado_renovacion(self) -> EstadoRenovacion:
        return self.e.renovaciones.obtener(self.renovacion.renovacion_id).estado

    @property
    def fin_de_la_poliza(self) -> date:
        return self.e.polizas.obtener(POLIZA).fecha_fin

    def hay_pendientes(self) -> int:
        return self.pendientes.listar(CLIENTE).total

    def aprobados(self) -> int:
        pagos = self.e.pagos.listar_por_cotizacion(self.renovacion.cotizacion_id)
        return sum(1 for p in pagos if p.estado is EstadoPago.APROBADO)


@pytest.fixture
def escenario() -> Escenario:
    return Escenario()


# --- Criterio 4: pago rechazado, nuevo intento ---------------------------------------------


def test_un_pago_rechazado_no_cambia_nada_y_la_prima_sigue_pendiente(escenario) -> None:
    pago, repetido = escenario.pagar("llave-0001", "tok_rechazado_1")

    assert pago.estado is EstadoPago.RECHAZADO and repetido is False
    assert pago.motivo_rechazo == "FONDOS_INSUFICIENTES"
    assert escenario.estado_renovacion is EstadoRenovacion.PENDIENTE_PAGO
    assert escenario.fin_de_la_poliza == date(2026, 12, 31)
    assert escenario.hay_pendientes() == 1
    with pytest.raises(PagoSinComprobante):
        escenario.comprobantes.obtener(pago)


def test_tras_el_rechazo_se_puede_intentar_de_nuevo_y_se_renueva(escenario) -> None:
    rechazado, _ = escenario.pagar("llave-0001", "tok_rechazado_1")

    aprobado, repetido = escenario.pagar("llave-0002")

    assert aprobado.estado is EstadoPago.APROBADO and repetido is False
    assert aprobado.pago_id != rechazado.pago_id
    assert escenario.estado_renovacion is EstadoRenovacion.APLICADA
    assert escenario.fin_de_la_poliza == date(2027, 12, 31)
    assert escenario.hay_pendientes() == 0
    assert escenario.comprobantes.obtener(aprobado).monto == escenario.renovacion.prima_total
    assert escenario.pasarela.llamadas == 2  # un intento rechazado y uno aprobado


def test_se_puede_reintentar_varias_veces_hasta_que_un_pago_se_apruebe(escenario) -> None:
    for intento in range(3):
        pago, _ = escenario.pagar(f"llave-rechazo-{intento}", "tok_rechazado_1")
        assert pago.estado is EstadoPago.RECHAZADO

    assert escenario.hay_pendientes() == 1
    assert escenario.pagar("llave-final")[0].estado is EstadoPago.APROBADO
    assert escenario.aprobados() == 1


# --- Criterio 5: un reintento nunca cobra dos veces ----------------------------------------


def test_reintentar_un_pago_ya_aprobado_devuelve_el_mismo_sin_cobrar(escenario) -> None:
    original, _ = escenario.pagar("llave-0001")

    # La respuesta se perdió y la app repite exactamente la misma solicitud.
    repetido, fue_repetido = escenario.pagar("llave-0001")

    assert fue_repetido is True and repetido == original
    assert escenario.pasarela.llamadas == 1
    assert escenario.aprobados() == 1
    assert len(escenario.e.pagos.listar_por_cotizacion(escenario.renovacion.cotizacion_id)) == 1
    assert escenario.estado_renovacion is EstadoRenovacion.APLICADA
    assert escenario.fin_de_la_poliza == date(2027, 12, 31)
    assert escenario.comprobantes.obtener(repetido) == escenario.comprobantes.obtener(original)


def test_un_pago_nuevo_sobre_una_renovacion_ya_pagada_se_rechaza_sin_cobrar(escenario) -> None:
    escenario.pagar("llave-0001")

    with pytest.raises(CotizacionNoPagable) as error:
        escenario.pagar("llave-0002")

    assert error.value.codigo == "COTIZACION_YA_PAGADA"
    assert escenario.pasarela.llamadas == 1
    assert escenario.aprobados() == 1


def test_si_la_pasarela_se_cae_el_reintento_con_la_misma_llave_no_vuelve_a_cobrar(
    escenario,
) -> None:
    with pytest.raises(PasarelaNoDisponible):
        escenario.pagar("llave-0001", "tok_caido_1")

    reintento, repetido = escenario.pagar("llave-0001", "tok_caido_1")

    assert repetido is True and reintento.estado is EstadoPago.PENDIENTE
    assert escenario.pasarela.llamadas == 1
    assert escenario.estado_renovacion is EstadoRenovacion.PENDIENTE_PAGO
    assert escenario.hay_pendientes() == 1


def test_el_reintento_con_la_misma_llave_pero_otro_cuerpo_se_rechaza(escenario) -> None:
    from app.pagos.servicio import LlaveIdempotenciaReutilizada

    escenario.pagar("llave-0001", "tok_rechazado_1")

    with pytest.raises(LlaveIdempotenciaReutilizada):
        escenario.pagar("llave-0001", "tok_visa_aprobado")

    assert escenario.pasarela.llamadas == 1


def test_si_el_aviso_del_pago_se_perdio_el_reintento_no_cobra_y_la_renovacion_se_aplica() -> None:
    escenario = Escenario(avisar_pagos=False)
    original, _ = escenario.pagar("llave-0001")
    assert escenario.estado_renovacion is EstadoRenovacion.PENDIENTE_PAGO  # no se enteró

    repetido, fue_repetido = escenario.pagar("llave-0001")
    # Al listar las primas pendientes se recupera el pago aprobado y se aplica.
    pendientes = escenario.hay_pendientes()

    assert fue_repetido is True and repetido == original
    assert escenario.pasarela.llamadas == 1
    assert pendientes == 0
    assert escenario.estado_renovacion is EstadoRenovacion.APLICADA
    assert escenario.aprobados() == 1
