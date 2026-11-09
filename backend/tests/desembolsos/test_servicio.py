"""Evaluación del siniestro y desembolso de la indemnización (HU15)."""

from decimal import Decimal

import pytest

from app.desembolsos.modelos import EstadoDesembolso, MedioDesembolso, SolicitudCuenta
from app.desembolsos.servicio import DesembolsoNoReintentable, SiniestroNoAprobado
from app.siniestros.evaluacion import MontoInvalido, SiniestroNoEncontrado, SiniestroYaEvaluado
from app.siniestros.modelos import EstadoSiniestro
from tests.desembolsos.fabrica import CLIENTE, OPERADOR, crear_entorno, cuenta, siniestro

# --- Cuenta del cliente ------------------------------------------------------------------


def test_la_cuenta_se_tokeniza_y_no_se_guarda_el_numero() -> None:
    e = crear_entorno()

    registrada = e.desembolsos.registrar_cuenta(CLIENTE, cuenta("4567891234"))

    assert registrada.ultimos_digitos == "1234"
    assert registrada.token_cuenta.startswith("CTA-")
    assert "4567891234" not in registrada.model_dump_json()
    assert registrada.enmascarada == "Bancolombia ahorros ****1234"


def test_el_numero_y_el_banco_se_validan() -> None:
    with pytest.raises(ValueError):
        SolicitudCuenta(codigo_banco="9999", tipo_cuenta="AHORROS", numero_cuenta="12345678")
    with pytest.raises(ValueError):
        SolicitudCuenta(codigo_banco="1007", tipo_cuenta="AHORROS", numero_cuenta="12AB5678")
    assert cuenta("1234-5678 90").numero_cuenta == "1234567890"


# --- Aprobación --------------------------------------------------------------------------


def test_aprobar_paga_a_la_cuenta_registrada() -> None:
    e = crear_entorno()
    e.desembolsos.registrar_cuenta(CLIENTE, cuenta())

    aprobado, desembolso = e.evaluacion.aprobar("SIN-1", OPERADOR)

    assert aprobado.estado is EstadoSiniestro.APROBADO
    assert aprobado.monto_aprobado == Decimal("850000.00")
    assert aprobado.evaluado_por == OPERADOR
    assert aprobado.evaluado_en is not None
    assert desembolso.medio is MedioDesembolso.CUENTA_BANCARIA
    assert desembolso.destino == "Bancolombia ahorros ****5678"
    assert desembolso.estado is EstadoDesembolso.COMPLETADA
    assert desembolso.referencia_transaccion.startswith("TRF-")
    assert desembolso.monto == Decimal("850000.00")
    assert e.siniestros.obtener("SIN-1").estado is EstadoSiniestro.APROBADO


def test_sin_cuenta_se_genera_un_codigo_de_retiro() -> None:
    e = crear_entorno()

    _, desembolso = e.evaluacion.aprobar("SIN-1", OPERADOR)

    assert desembolso.medio is MedioDesembolso.CODIGO_RETIRO
    assert desembolso.estado is EstadoDesembolso.COMPLETADA
    assert desembolso.codigo_retiro is not None and len(desembolso.codigo_retiro) == 8
    assert desembolso.referencia_transaccion.startswith("RET-")


def test_el_monto_tiene_tope_en_la_suma_asegurada() -> None:
    caro = siniestro(estimacion_danos=Decimal("90000000.00"))
    e = crear_entorno(caro)

    aprobado, _ = e.evaluacion.aprobar("SIN-1", OPERADOR)
    assert aprobado.monto_aprobado == Decimal("40000000.00")

    otro = crear_entorno()
    with pytest.raises(MontoInvalido):
        otro.evaluacion.aprobar("SIN-1", OPERADOR, Decimal("40000000.01"))


def test_operaciones_puede_aprobar_otro_monto() -> None:
    e = crear_entorno()

    aprobado, desembolso = e.evaluacion.aprobar("SIN-1", OPERADOR, Decimal("600000"))

    assert aprobado.monto_aprobado == Decimal("600000.00")
    assert desembolso.monto == Decimal("600000.00")


def test_aprobar_dos_veces_no_paga_dos_veces() -> None:
    e = crear_entorno()

    _, primero = e.evaluacion.aprobar("SIN-1", OPERADOR)
    _, segundo = e.evaluacion.aprobar("SIN-1", OPERADOR)

    assert segundo.desembolso_id == primero.desembolso_id
    assert len(e.red.retiros) == 1


def test_aprobar_de_nuevo_por_otro_monto_se_rechaza() -> None:
    e = crear_entorno()
    e.evaluacion.aprobar("SIN-1", OPERADOR)

    with pytest.raises(SiniestroYaEvaluado):
        e.evaluacion.aprobar("SIN-1", OPERADOR, Decimal("100000"))


def test_dos_aprobaciones_simultaneas_crean_un_solo_desembolso() -> None:
    e = crear_entorno()
    aprobado = siniestro(
        estado=EstadoSiniestro.APROBADO,
        monto_aprobado=Decimal("850000.00"),
        evaluado_por=OPERADOR,
    )
    # Simula que la otra petición creó el desembolso entre la lectura y la creación.
    leer = e.repo_desembolsos.obtener_por_siniestro
    primero = e.desembolsos.desembolsar(aprobado)
    vistas = iter([None, primero])
    e.repo_desembolsos.obtener_por_siniestro = lambda _id: next(vistas)

    segundo = e.desembolsos.desembolsar(aprobado)

    e.repo_desembolsos.obtener_por_siniestro = leer
    assert segundo.desembolso_id == primero.desembolso_id
    assert len(e.red.retiros) == 1


def test_un_siniestro_rechazado_no_se_aprueba_ni_se_paga() -> None:
    e = crear_entorno()
    rechazado = e.evaluacion.rechazar("SIN-1", OPERADOR, "El evento no está cubierto.")

    assert rechazado.estado is EstadoSiniestro.RECHAZADO
    assert rechazado.motivo_rechazo == "El evento no está cubierto."
    with pytest.raises(SiniestroYaEvaluado):
        e.evaluacion.aprobar("SIN-1", OPERADOR)
    assert e.desembolsos.obtener_por_siniestro("SIN-1") is None
    # Rechazar de nuevo es inocuo; rechazar uno aprobado, no.
    assert e.evaluacion.rechazar("SIN-1", OPERADOR, "Otra vez").motivo_rechazo == (
        "El evento no está cubierto."
    )


def test_un_siniestro_aprobado_no_se_rechaza() -> None:
    e = crear_entorno()
    e.evaluacion.aprobar("SIN-1", OPERADOR)

    with pytest.raises(SiniestroYaEvaluado):
        e.evaluacion.rechazar("SIN-1", OPERADOR, "Cambié de opinión")


def test_solo_se_desembolsa_un_siniestro_aprobado() -> None:
    e = crear_entorno()

    with pytest.raises(SiniestroNoAprobado):
        e.desembolsos.desembolsar(siniestro())


def test_un_siniestro_inexistente_no_se_evalua() -> None:
    e = crear_entorno()

    with pytest.raises(SiniestroNoEncontrado):
        e.evaluacion.aprobar("SIN-NADA", OPERADOR)


# --- Fallos de la red --------------------------------------------------------------------


def test_si_la_red_no_responde_queda_pendiente_y_se_reintenta_sin_duplicar() -> None:
    e = crear_entorno()
    e.desembolsos.registrar_cuenta(CLIENTE, cuenta())
    e.red.caida = True

    _, pendiente = e.evaluacion.aprobar("SIN-1", OPERADOR)

    assert pendiente.estado is EstadoDesembolso.PENDIENTE
    assert pendiente.motivo_fallo == "RED_NO_DISPONIBLE"
    assert e.siniestros.obtener("SIN-1").estado is EstadoSiniestro.APROBADO

    e.red.caida = False
    completado = e.evaluacion.reintentar_desembolso("SIN-1")

    assert completado.estado is EstadoDesembolso.COMPLETADA
    assert completado.intento == 1  # misma referencia frente a la red
    assert e.red.transferencias == [pendiente.referencia_interna]


def test_una_cuenta_inexistente_falla_y_se_reintenta_con_la_cuenta_corregida() -> None:
    e = crear_entorno()
    e.desembolsos.registrar_cuenta(CLIENTE, cuenta("11110000"))

    _, fallido = e.evaluacion.aprobar("SIN-1", OPERADOR)

    assert fallido.estado is EstadoDesembolso.FALLIDA
    assert fallido.motivo_fallo == "CUENTA_INEXISTENTE"
    assert fallido.referencia_transaccion is not None

    e.desembolsos.registrar_cuenta(CLIENTE, cuenta("11112222"))
    corregido = e.evaluacion.reintentar_desembolso("SIN-1")

    assert corregido.estado is EstadoDesembolso.COMPLETADA
    assert corregido.intento == 2
    assert corregido.destino.endswith("****2222")
    assert corregido.desembolso_id == fallido.desembolso_id


def test_reintentar_sin_desembolso_lo_crea() -> None:
    e = crear_entorno(
        siniestro(
            estado=EstadoSiniestro.APROBADO,
            monto_aprobado=Decimal("850000.00"),
            evaluado_por=OPERADOR,
        )
    )

    desembolso = e.evaluacion.reintentar_desembolso("SIN-1")

    assert desembolso.estado is EstadoDesembolso.COMPLETADA


def test_reintentar_un_siniestro_sin_aprobar_se_rechaza() -> None:
    e = crear_entorno()

    with pytest.raises(SiniestroYaEvaluado):
        e.evaluacion.reintentar_desembolso("SIN-1")


def test_un_desembolso_completado_no_se_reintenta() -> None:
    e = crear_entorno()
    e.evaluacion.aprobar("SIN-1", OPERADOR)

    with pytest.raises(DesembolsoNoReintentable):
        e.evaluacion.reintentar_desembolso("SIN-1")


# --- Bandeja -----------------------------------------------------------------------------


def test_la_bandeja_filtra_por_estado_y_trae_el_desembolso() -> None:
    e = crear_entorno(siniestro(), siniestro(siniestro_id="SIN-2"))
    e.evaluacion.aprobar("SIN-1", OPERADOR)

    pendientes = e.evaluacion.bandeja(EstadoSiniestro.REGISTRADO)
    todos = dict((s.siniestro_id, d) for s, d in e.evaluacion.bandeja())

    assert [s.siniestro_id for s, _ in pendientes] == ["SIN-2"]
    assert todos["SIN-1"].estado is EstadoDesembolso.COMPLETADA
    assert todos["SIN-2"] is None
