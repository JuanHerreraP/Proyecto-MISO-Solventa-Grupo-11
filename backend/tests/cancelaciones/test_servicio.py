"""Casos de uso de la cancelación: confirmar, idempotencia y bloqueos (HU22)."""

from decimal import Decimal

import pytest

from app.desembolsos.modelos import EstadoDesembolso
from app.identidad.modelos import Rol
from app.polizas.dominio.cancelacion import (
    CancelacionNoPermitida,
    CodigoBloqueo,
    ConfirmacionRequerida,
    EstadoDevolucion,
    MotivoCancelacion,
)
from app.polizas.dominio.modelos import EstadoRegistroPoliza
from app.polizas.emision import AccesoDenegado
from app.polizas.endosos import ClaveIdempotenciaReutilizada, Solicitante
from app.polizas.servicio import PolizaNoEncontrada
from app.siniestros.modelos import EstadoSiniestro
from tests.cancelaciones.fabrica import (
    AHORA,
    ASESOR,
    CLIENTE,
    POLIZA,
    TITULAR,
    crear_entorno,
    desembolso,
    siniestro,
    solicitud,
)


def test_confirmar_cancela_la_poliza_y_registra_la_cancelacion() -> None:
    entorno = crear_entorno()

    cancelacion, creada = entorno.servicio.confirmar(TITULAR, POLIZA, solicitud(detalle="Me mudo"))

    assert creada is True
    assert cancelacion.saldo_estimado == Decimal("74794.52")
    assert cancelacion.estado_devolucion is EstadoDevolucion.PENDIENTE
    assert cancelacion.solicitado_por == CLIENTE
    assert cancelacion.rol_solicitante == "CLIENTE"
    assert cancelacion.ip_solicitante == "10.0.0.1"
    assert cancelacion.detalle == "Me mudo"
    guardada = entorno.polizas.obtener(POLIZA)
    assert guardada.estado is EstadoRegistroPoliza.CANCELADA
    assert guardada.cancelada_en == AHORA
    assert entorno.cancelaciones.por_poliza(POLIZA) == cancelacion


def test_sin_saldo_la_devolucion_queda_sin_saldo() -> None:
    entorno = crear_entorno(fecha_inicio=AHORA.date().replace(month=1, day=1))
    entorno.polizas.guardar(
        entorno.polizas.obtener(POLIZA).model_copy(update={"fecha_fin": AHORA.date()})
    )

    cancelacion, _ = entorno.servicio.confirmar(TITULAR, POLIZA, solicitud())

    assert cancelacion.saldo_estimado == Decimal("0.00")
    assert cancelacion.estado_devolucion is EstadoDevolucion.SIN_SALDO


def test_sin_confirmacion_explicita_no_se_cancela() -> None:
    entorno = crear_entorno()

    with pytest.raises(ConfirmacionRequerida):
        entorno.servicio.confirmar(TITULAR, POLIZA, solicitud(confirmo=False))

    assert entorno.polizas.obtener(POLIZA).estado is EstadoRegistroPoliza.VIGENTE
    assert entorno.cancelaciones.por_poliza(POLIZA) is None


def test_una_poliza_ajena_se_trata_como_inexistente() -> None:
    entorno = crear_entorno()

    with pytest.raises(PolizaNoEncontrada):
        entorno.servicio.confirmar(Solicitante("CLI-OTRO", Rol.CLIENTE), POLIZA, solicitud())
    with pytest.raises(PolizaNoEncontrada):
        entorno.servicio.consultar(Solicitante("CLI-OTRO", Rol.CLIENTE), POLIZA)
    with pytest.raises(PolizaNoEncontrada):
        entorno.servicio.consultar(TITULAR, "POL-NO-EXISTE")

    assert entorno.polizas.obtener(POLIZA).estado is EstadoRegistroPoliza.VIGENTE


def test_repetir_la_misma_solicitud_con_la_misma_clave_devuelve_la_misma_cancelacion() -> None:
    entorno = crear_entorno()

    primera, creada1 = entorno.servicio.confirmar(
        TITULAR, POLIZA, solicitud(), clave_idempotencia="clave-1"
    )
    entorno.reloj.avanzar(minutes=5)
    segunda, creada2 = entorno.servicio.confirmar(
        TITULAR, POLIZA, solicitud(), clave_idempotencia="clave-1"
    )

    assert (creada1, creada2) == (True, False)
    assert segunda == primera


def test_reusar_la_clave_con_otro_motivo_se_rechaza() -> None:
    entorno = crear_entorno()
    entorno.servicio.confirmar(TITULAR, POLIZA, solicitud(), clave_idempotencia="clave-1")

    with pytest.raises(ClaveIdempotenciaReutilizada):
        entorno.servicio.confirmar(
            TITULAR,
            POLIZA,
            solicitud(motivo=MotivoCancelacion.PRECIO_ALTO),
            clave_idempotencia="clave-1",
        )


def test_cancelar_dos_veces_con_claves_distintas_se_rechaza() -> None:
    entorno = crear_entorno()
    entorno.servicio.confirmar(TITULAR, POLIZA, solicitud(), clave_idempotencia="clave-1")

    with pytest.raises(CancelacionNoPermitida) as error:
        entorno.servicio.confirmar(TITULAR, POLIZA, solicitud(), clave_idempotencia="clave-2")

    assert error.value.bloqueos[0].codigo is CodigoBloqueo.POLIZA_NO_VIGENTE


@pytest.mark.parametrize("estado", [EstadoSiniestro.REGISTRADO, EstadoSiniestro.EN_EVALUACION])
def test_un_siniestro_en_tramite_impide_cancelar_y_deja_la_poliza_igual(estado) -> None:
    entorno = crear_entorno()
    entorno.siniestros.guardar(siniestro(estado))

    with pytest.raises(CancelacionNoPermitida) as error:
        entorno.servicio.confirmar(TITULAR, POLIZA, solicitud())

    assert error.value.bloqueos[0].codigo is CodigoBloqueo.SINIESTRO_EN_TRAMITE
    assert error.value.bloqueos[0].siniestros == ("SIN-1",)
    assert entorno.polizas.obtener(POLIZA).estado is EstadoRegistroPoliza.VIGENTE
    assert entorno.cancelaciones.por_poliza(POLIZA) is None


def test_un_siniestro_aprobado_sin_desembolso_completo_sigue_en_tramite() -> None:
    entorno = crear_entorno()
    entorno.siniestros.guardar(siniestro(EstadoSiniestro.APROBADO))

    propuesta, _ = entorno.servicio.consultar(TITULAR, POLIZA)
    assert propuesta.cancelable is False

    entorno.desembolsos.guardar(desembolso(EstadoDesembolso.PENDIENTE))
    propuesta, _ = entorno.servicio.consultar(TITULAR, POLIZA)
    assert propuesta.cancelable is False

    entorno.desembolsos.guardar(desembolso(EstadoDesembolso.FALLIDA))
    propuesta, _ = entorno.servicio.consultar(TITULAR, POLIZA)
    assert propuesta.cancelable is False


def test_un_siniestro_aprobado_y_desembolsado_ya_no_bloquea() -> None:
    entorno = crear_entorno()
    entorno.siniestros.guardar(siniestro(EstadoSiniestro.APROBADO))
    entorno.desembolsos.guardar(desembolso(EstadoDesembolso.COMPLETADA))

    cancelacion, creada = entorno.servicio.confirmar(TITULAR, POLIZA, solicitud())

    assert creada is True
    assert cancelacion.poliza_id == POLIZA


def test_un_siniestro_rechazado_no_bloquea() -> None:
    entorno = crear_entorno()
    entorno.siniestros.guardar(siniestro(EstadoSiniestro.RECHAZADO))

    propuesta, _ = entorno.servicio.consultar(TITULAR, POLIZA)

    assert propuesta.cancelable is True


def test_consultar_no_modifica_nada_y_devuelve_la_cancelacion_si_ya_existe() -> None:
    entorno = crear_entorno()

    propuesta, cancelacion = entorno.servicio.consultar(TITULAR, POLIZA)
    assert propuesta.cancelable is True and cancelacion is None
    assert entorno.polizas.obtener(POLIZA).estado is EstadoRegistroPoliza.VIGENTE

    creada, _ = entorno.servicio.confirmar(TITULAR, POLIZA, solicitud())
    propuesta, cancelacion = entorno.servicio.consultar(TITULAR, POLIZA)

    assert propuesta.cancelable is False
    assert cancelacion == creada


def test_el_asesor_cancela_una_poliza_de_su_venta_asistida() -> None:
    entorno = crear_entorno(asesor_id="ASE-1")

    cancelacion, creada = entorno.servicio.confirmar(ASESOR, POLIZA, solicitud())

    assert creada is True
    assert cancelacion.solicitado_por == "ASE-1"
    assert cancelacion.rol_solicitante == "ASESOR_VENTAS"
    assert entorno.polizas.obtener(POLIZA).estado is EstadoRegistroPoliza.CANCELADA


def test_el_asesor_puede_consultar_las_condiciones_de_su_venta() -> None:
    entorno = crear_entorno(asesor_id="ASE-1")

    propuesta, cancelacion = entorno.servicio.consultar(ASESOR, POLIZA)

    assert propuesta.cancelable is True and cancelacion is None


def test_el_asesor_no_cancela_la_poliza_de_otro_asesor_ni_una_sin_asesor() -> None:
    for asesor_de_la_venta in ("ASE-2", None):
        entorno = crear_entorno(asesor_id=asesor_de_la_venta)

        with pytest.raises(AccesoDenegado):
            entorno.servicio.confirmar(ASESOR, POLIZA, solicitud())
        with pytest.raises(AccesoDenegado):
            entorno.servicio.consultar(ASESOR, POLIZA)

        assert entorno.polizas.obtener(POLIZA).estado is EstadoRegistroPoliza.VIGENTE


def test_el_asesor_tambien_respeta_los_bloqueos() -> None:
    entorno = crear_entorno(asesor_id="ASE-1")
    entorno.siniestros.guardar(siniestro(EstadoSiniestro.REGISTRADO))

    with pytest.raises(CancelacionNoPermitida):
        entorno.servicio.confirmar(ASESOR, POLIZA, solicitud())


def test_un_rol_sin_permiso_no_cancela() -> None:
    entorno = crear_entorno()

    with pytest.raises(AccesoDenegado):
        entorno.servicio.confirmar(Solicitante("ANA-1", Rol.ANALISTA_RIESGOS), POLIZA, solicitud())
