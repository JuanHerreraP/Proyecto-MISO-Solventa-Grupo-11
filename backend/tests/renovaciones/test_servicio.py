"""Casos de uso de la renovación: propuesta, inicio, pago y aplicación (HU22)."""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.cotizaciones.dominio.modelos import EstadoCotizacion
from app.identidad.modelos import Rol
from app.pagos.modelos import EstadoPago, MetodoPago, SolicitudPago
from app.pagos.servicio import firmar
from app.perfilamiento.dominio.modelos import Dictamen
from app.polizas.dominio.modelos import (
    CoberturaPoliza,
    EstadoRegistroPoliza,
    RamoPoliza,
)
from app.polizas.dominio.renovacion import (
    CodigoBloqueoRenovacion,
    EstadoRenovacion,
    RenovacionNoEncontrada,
    RenovacionNoPermitida,
    renovacion_id_de,
)
from app.polizas.emision import AccesoDenegado
from app.polizas.endosos import Solicitante
from app.polizas.servicio import PolizaNoEncontrada
from tests.renovaciones.fabrica import (
    AHORA,
    ASESOR,
    CLIENTE,
    COTIZACION,
    DATOS_VIDA,
    POLIZA,
    PRIMA_RENOVADA,
    TITULAR,
    crear_entorno,
    perfil,
    solicitud_pago,
)

NUEVO_ID = renovacion_id_de(POLIZA, date(2027, 1, 1))
INCAPACIDAD = CoberturaPoliza(
    codigo="INCAPACIDAD_TOTAL_PERMANENTE",
    nombre="Incapacidad total y permanente",
    suma_asegurada=Decimal("50000000.00"),
)


def codigos(error: RenovacionNoPermitida) -> list[CodigoBloqueoRenovacion]:
    return [b.codigo for b in error.bloqueos]


# --- Propuesta: lo que se ve antes de confirmar (criterio 1) ------------------------------


def test_la_propuesta_muestra_nueva_vigencia_coberturas_y_prima() -> None:
    entorno = crear_entorno()

    propuesta, pendiente = entorno.servicio.consultar(TITULAR, POLIZA)

    assert propuesta.renovable is True and propuesta.bloqueos == ()
    assert pendiente is None
    assert (propuesta.vigencia_actual.inicio, propuesta.vigencia_actual.fin) == (
        date(2026, 1, 1),
        date(2026, 12, 31),
    )
    assert (propuesta.nueva_vigencia.inicio, propuesta.nueva_vigencia.fin) == (
        date(2027, 1, 1),
        date(2027, 12, 31),
    )
    assert propuesta.prima_actual == Decimal("150000.00")
    assert propuesta.prima_nueva == PRIMA_RENOVADA
    assert propuesta.prima_principal == PRIMA_RENOVADA
    assert propuesta.prima_opcionales == Decimal("0.00")
    assert propuesta.personalizada is False
    assert [c.codigo for c in propuesta.coberturas] == ["FALLECIMIENTO"]
    assert propuesta.coberturas[0].suma_asegurada == Decimal("100000000.00")
    assert propuesta.renovable_desde == date(2026, 12, 1)
    assert len(propuesta.condiciones) == 4


def test_consultar_no_guarda_nada() -> None:
    entorno = crear_entorno()

    entorno.servicio.consultar(TITULAR, POLIZA)

    assert entorno.renovaciones.por_poliza(POLIZA) == []
    assert entorno.polizas.obtener(POLIZA).fecha_fin == date(2026, 12, 31)


def test_las_coberturas_opcionales_de_los_endosos_se_incluyen_en_la_prima() -> None:
    entorno = crear_entorno(coberturas_opcionales=[INCAPACIDAD])

    propuesta, _ = entorno.servicio.consultar(TITULAR, POLIZA)

    # 50 millones x 0,00012 x (365 días / 30) = 73.000
    assert propuesta.prima_opcionales == Decimal("73000.00")
    assert propuesta.prima_nueva == Decimal("493000.00")
    opcional = propuesta.coberturas[1]
    assert (opcional.codigo, opcional.principal, opcional.prima) == (
        "INCAPACIDAD_TOTAL_PERMANENTE",
        False,
        Decimal("73000.00"),
    )


def test_la_prima_se_recalcula_con_el_perfil_de_riesgo_vigente() -> None:
    entorno = crear_entorno(perfil_riesgo=perfil(factor=1.2))

    propuesta, _ = entorno.servicio.consultar(TITULAR, POLIZA)

    assert propuesta.prima_nueva == Decimal("504000.00")  # 420.000 x 1,2
    assert propuesta.personalizada is True


def test_un_perfil_rechazado_impide_renovar_y_lo_explica() -> None:
    entorno = crear_entorno(perfil_riesgo=perfil(dictamen=Dictamen.RECHAZADO, factor=None))

    propuesta, _ = entorno.servicio.consultar(TITULAR, POLIZA)

    assert propuesta.renovable is False
    assert propuesta.bloqueos[0].codigo is CodigoBloqueoRenovacion.RIESGO_NO_ASEGURABLE
    assert propuesta.nueva_vigencia is None and propuesta.prima_nueva is None
    with pytest.raises(RenovacionNoPermitida) as error:
        entorno.servicio.iniciar(TITULAR, POLIZA)
    assert codigos(error.value) == [CodigoBloqueoRenovacion.RIESGO_NO_ASEGURABLE]


def test_sin_los_datos_del_riesgo_no_se_puede_cotizar_la_renovacion() -> None:
    entorno = crear_entorno(con_cotizacion=False)

    propuesta, _ = entorno.servicio.consultar(TITULAR, POLIZA)

    assert propuesta.bloqueos[0].codigo is CodigoBloqueoRenovacion.SIN_DATOS_DE_RIESGO


def test_datos_del_riesgo_que_ya_no_son_validos_impiden_renovar() -> None:
    entorno = crear_entorno(datos_riesgo={"meses_cobertura": 12})

    propuesta, _ = entorno.servicio.consultar(TITULAR, POLIZA)

    assert propuesta.bloqueos[0].codigo is CodigoBloqueoRenovacion.SIN_DATOS_DE_RIESGO


def test_proteccion_de_dispositivos_se_renueva_con_su_propia_tarifa() -> None:
    datos = {
        "tipo_dispositivo": "CELULAR",
        "marca": "Samsung",
        "modelo": "S24",
        "valor_dispositivo": "2000000",
        "fecha_compra": "2025-01-10",
        "meses_cobertura": 12,
    }
    entorno = crear_entorno(ramo=RamoPoliza.PROTECCION_DISPOSITIVOS, datos_riesgo=datos)

    propuesta, _ = entorno.servicio.consultar(TITULAR, POLIZA)

    assert propuesta.renovable is True
    assert propuesta.prima_nueva == Decimal("168000.00")  # 2 millones x 0,007 x 12


def test_el_seguro_parametrico_se_renueva_con_el_periodo_siguiente() -> None:
    datos = {
        "tipo_evento": "RETRASO_VUELO",
        "numero_vuelo": "AV123",
        "fecha_inicio": "2026-01-01",
        "fecha_fin": "2026-12-31",
        "umbral_disparo": "120",
        "valor_asegurado": "1000000",
    }
    entorno = crear_entorno(ramo=RamoPoliza.PARAMETRICO, datos_riesgo=datos)

    propuesta, _ = entorno.servicio.consultar(TITULAR, POLIZA)

    assert propuesta.renovable is True
    assert (propuesta.nueva_vigencia.inicio, propuesta.nueva_vigencia.fin) == (
        date(2027, 1, 1),
        date(2027, 12, 31),
    )
    assert propuesta.prima_nueva == Decimal("50000.00")  # 1 millón x 5 %


@pytest.mark.parametrize(
    ("cambios", "hoy", "esperado"),
    [
        ({}, datetime(2026, 11, 30, 15, tzinfo=UTC), CodigoBloqueoRenovacion.FUERA_DE_VENTANA),
        ({}, datetime(2027, 1, 2, 15, tzinfo=UTC), CodigoBloqueoRenovacion.POLIZA_NO_VIGENTE),
        (
            {"ramo": RamoPoliza.VIAJE},
            AHORA,
            CodigoBloqueoRenovacion.RAMO_NO_RENOVABLE,
        ),
        (
            {
                "estado": EstadoRegistroPoliza.CANCELADA,
                "cancelada_en": datetime(2026, 12, 5, 15, tzinfo=UTC),
            },
            AHORA,
            CodigoBloqueoRenovacion.POLIZA_NO_VIGENTE,
        ),
    ],
)
def test_si_no_se_puede_renovar_se_informa_la_razon(cambios, hoy, esperado) -> None:
    entorno = crear_entorno(**cambios)
    entorno.reloj.ahora = hoy

    propuesta, _ = entorno.servicio.consultar(TITULAR, POLIZA)
    with pytest.raises(RenovacionNoPermitida) as error:
        entorno.servicio.iniciar(TITULAR, POLIZA)

    assert propuesta.renovable is False
    assert [b.codigo for b in propuesta.bloqueos] == [esperado]
    assert codigos(error.value) == [esperado]
    assert propuesta.nueva_vigencia is None
    assert entorno.renovaciones.por_poliza(POLIZA) == []


# --- Inicio y pago (criterio 2) -----------------------------------------------------------


def test_iniciar_crea_la_cotizacion_de_renovacion_y_no_toca_la_poliza() -> None:
    entorno = crear_entorno()

    renovacion, creada = entorno.servicio.iniciar(TITULAR, POLIZA, "clave-1")

    assert creada is True
    assert renovacion.renovacion_id == NUEVO_ID
    assert renovacion.estado is EstadoRenovacion.PENDIENTE_PAGO
    assert renovacion.prima_total == PRIMA_RENOVADA
    assert (renovacion.anterior_inicio, renovacion.anterior_fin) == (
        date(2026, 1, 1),
        date(2026, 12, 31),
    )
    assert renovacion.solicitado_por == CLIENTE and renovacion.rol_solicitante == "CLIENTE"
    assert renovacion.ip_solicitante == "10.0.0.1"
    cotizacion = entorno.cotizaciones.obtener(renovacion.cotizacion_id)
    assert cotizacion.estado is EstadoCotizacion.VIGENTE
    assert cotizacion.cliente_id == CLIENTE
    assert cotizacion.prima_total == PRIMA_RENOVADA
    assert cotizacion.cobertura_principal.codigo == "FALLECIMIENTO"
    assert cotizacion.datos_riesgo["meses_cobertura"] == 12
    assert cotizacion.vigente_hasta == AHORA + timedelta(days=7)
    assert renovacion.vigente_hasta == cotizacion.vigente_hasta
    poliza = entorno.polizas.obtener(POLIZA)
    assert poliza.fecha_fin == date(2026, 12, 31) and poliza.prima_total == Decimal("150000.00")


def test_la_cotizacion_de_renovacion_guarda_las_fechas_nuevas_del_riesgo() -> None:
    datos = {
        "tipo_evento": "RETRASO_VUELO",
        "numero_vuelo": "AV123",
        "fecha_inicio": "2026-01-01",
        "fecha_fin": "2026-12-31",
        "umbral_disparo": "120",
        "valor_asegurado": "1000000",
    }
    entorno = crear_entorno(ramo=RamoPoliza.PARAMETRICO, datos_riesgo=datos)

    renovacion, _ = entorno.servicio.iniciar(TITULAR, POLIZA)

    cotizacion = entorno.cotizaciones.obtener(renovacion.cotizacion_id)
    assert cotizacion.datos_riesgo["fecha_inicio"] == "2027-01-01"
    assert cotizacion.datos_riesgo["fecha_fin"] == "2027-12-31"
    original = entorno.cotizaciones.obtener(COTIZACION)
    assert original.datos_riesgo["fecha_inicio"] == "2026-01-01"


def test_iniciar_dos_veces_devuelve_la_misma_renovacion() -> None:
    entorno = crear_entorno()
    primera, _ = entorno.servicio.iniciar(TITULAR, POLIZA, "clave-1")

    con_la_misma_clave, creada1 = entorno.servicio.iniciar(TITULAR, POLIZA, "clave-1")
    con_otra_clave, creada2 = entorno.servicio.iniciar(TITULAR, POLIZA, "clave-2")

    assert (creada1, creada2) == (False, False)
    assert con_la_misma_clave == primera and con_otra_clave == primera
    assert len(entorno.renovaciones.por_poliza(POLIZA)) == 1


def test_el_pago_aprobado_renueva_la_poliza() -> None:
    entorno = crear_entorno(coberturas_opcionales=[INCAPACIDAD])
    renovacion, _ = entorno.servicio.iniciar(TITULAR, POLIZA)

    pago = entorno.pagar(renovacion.cotizacion_id)

    assert pago.estado is EstadoPago.APROBADO and pago.monto == Decimal("493000.00")
    poliza = entorno.polizas.obtener(POLIZA)
    assert (poliza.fecha_inicio, poliza.fecha_fin) == (date(2027, 1, 1), date(2027, 12, 31))
    assert poliza.prima_total == Decimal("493000.00")
    assert poliza.numero_poliza == "SOL-2026-VIDA0001"
    assert poliza.estado is EstadoRegistroPoliza.VIGENTE
    assert [c.codigo for c in poliza.coberturas_opcionales] == ["INCAPACIDAD_TOTAL_PERMANENTE"]
    aplicada = entorno.renovaciones.obtener(NUEVO_ID)
    assert aplicada.estado is EstadoRenovacion.APLICADA
    assert aplicada.pago_id == pago.pago_id and aplicada.aplicada_en == AHORA
    assert entorno.cotizaciones.obtener(renovacion.cotizacion_id).estado is (
        EstadoCotizacion.ACEPTADA
    )


def test_despues_de_renovar_ya_no_se_ofrece_renovar_de_nuevo() -> None:
    entorno = crear_entorno()
    renovacion, _ = entorno.servicio.iniciar(TITULAR, POLIZA)
    entorno.pagar(renovacion.cotizacion_id)

    propuesta, pendiente = entorno.servicio.consultar(TITULAR, POLIZA)

    assert propuesta.renovable is False
    assert propuesta.bloqueos[0].codigo is CodigoBloqueoRenovacion.YA_RENOVADA
    assert pendiente is None
    with pytest.raises(RenovacionNoPermitida):
        entorno.servicio.iniciar(TITULAR, POLIZA)


def test_un_pago_rechazado_deja_la_poliza_como_estaba_y_se_puede_reintentar() -> None:
    entorno = crear_entorno()
    renovacion, _ = entorno.servicio.iniciar(TITULAR, POLIZA)

    rechazado = entorno.pagar(renovacion.cotizacion_id, token="tok_rechazado_1")

    assert rechazado.estado is EstadoPago.RECHAZADO
    assert rechazado.motivo_rechazo == "FONDOS_INSUFICIENTES"
    poliza = entorno.polizas.obtener(POLIZA)
    assert poliza.fecha_fin == date(2026, 12, 31) and poliza.prima_total == Decimal("150000.00")
    estado = entorno.servicio.obtener(TITULAR, POLIZA, NUEVO_ID)
    assert estado.estado is EstadoRenovacion.PENDIENTE_PAGO
    _, pendiente = entorno.servicio.consultar(TITULAR, POLIZA)
    assert pendiente.renovacion_id == NUEVO_ID

    entorno.pagar(renovacion.cotizacion_id, llave="llave-0002")

    assert entorno.polizas.obtener(POLIZA).fecha_fin == date(2027, 12, 31)
    assert entorno.servicio.obtener(TITULAR, POLIZA, NUEVO_ID).estado is EstadoRenovacion.APLICADA


def test_un_pago_pse_pendiente_renueva_cuando_la_pasarela_lo_confirma(monkeypatch) -> None:
    monkeypatch.setenv("PAGOS_WEBHOOK_SECRET", "secreto-de-pruebas")
    entorno = crear_entorno()
    renovacion, _ = entorno.servicio.iniciar(TITULAR, POLIZA)
    pago, _ = entorno.pagos_servicio.pagar(
        CLIENTE,
        "llave-pse-01",
        SolicitudPago(
            cotizacion_id=renovacion.cotizacion_id, metodo=MetodoPago.PSE, codigo_banco="1007"
        ),
    )
    assert pago.estado is EstadoPago.PENDIENTE
    assert entorno.polizas.obtener(POLIZA).fecha_fin == date(2026, 12, 31)

    cuerpo = json.dumps({"referencia": pago.referencia_pasarela, "estado": "APROBADO"}).encode()
    entorno.pagos_servicio.confirmar(
        cuerpo,
        firmar(cuerpo, b"secreto-de-pruebas"),
        pago.referencia_pasarela,
        EstadoPago.APROBADO,
    )

    assert entorno.polizas.obtener(POLIZA).fecha_fin == date(2027, 12, 31)
    assert entorno.renovaciones.obtener(NUEVO_ID).estado is EstadoRenovacion.APLICADA


def test_una_renovacion_sin_pagar_vence_con_su_cotizacion() -> None:
    entorno = crear_entorno()
    renovacion, _ = entorno.servicio.iniciar(TITULAR, POLIZA)

    entorno.reloj.avanzar(days=8)  # 18 de diciembre: aún dentro de la ventana de la póliza

    vista = entorno.servicio.obtener(TITULAR, POLIZA, NUEVO_ID)
    assert entorno.servicio.estado_de(vista) is EstadoRenovacion.VENCIDA
    propuesta, pendiente = entorno.servicio.consultar(TITULAR, POLIZA)
    assert propuesta.renovable is True and pendiente is None
    assert entorno.polizas.obtener(POLIZA).fecha_fin == date(2026, 12, 31)
    assert renovacion.cotizacion_id == vista.cotizacion_id


def test_tras_vencer_se_puede_iniciar_otra_renovacion_con_una_cotizacion_nueva() -> None:
    entorno = crear_entorno()
    vencida, _ = entorno.servicio.iniciar(TITULAR, POLIZA)
    entorno.reloj.avanzar(days=8)

    nueva, creada = entorno.servicio.iniciar(TITULAR, POLIZA)

    assert creada is True
    assert nueva.renovacion_id == vencida.renovacion_id
    assert nueva.cotizacion_id != vencida.cotizacion_id
    assert entorno.servicio.estado_de(nueva) is EstadoRenovacion.PENDIENTE_PAGO
    assert len(entorno.renovaciones.por_poliza(POLIZA)) == 1
    entorno.pagar(nueva.cotizacion_id)
    assert entorno.polizas.obtener(POLIZA).fecha_fin == date(2027, 12, 31)


# --- Robustez -----------------------------------------------------------------------------


def test_si_el_aviso_del_pago_falla_la_consulta_posterior_aplica_la_renovacion() -> None:
    entorno = crear_entorno(avisar_pagos=False)
    renovacion, _ = entorno.servicio.iniciar(TITULAR, POLIZA)
    entorno.pagar(renovacion.cotizacion_id)
    assert entorno.polizas.obtener(POLIZA).fecha_fin == date(2026, 12, 31)

    propuesta, pendiente = entorno.servicio.consultar(TITULAR, POLIZA)

    assert entorno.polizas.obtener(POLIZA).fecha_fin == date(2027, 12, 31)
    assert propuesta.bloqueos[0].codigo is CodigoBloqueoRenovacion.YA_RENOVADA
    assert pendiente is None
    assert entorno.renovaciones.obtener(NUEVO_ID).estado is EstadoRenovacion.APLICADA


def test_un_error_al_aplicar_no_deshace_el_pago(monkeypatch) -> None:
    entorno = crear_entorno()
    renovacion, _ = entorno.servicio.iniciar(TITULAR, POLIZA)

    def falla(*_):
        raise RuntimeError("base de datos caída")

    monkeypatch.setattr(entorno.renovaciones, "aplicar", falla)

    pago = entorno.pagar(renovacion.cotizacion_id)

    assert pago.estado is EstadoPago.APROBADO
    assert entorno.polizas.obtener(POLIZA).fecha_fin == date(2026, 12, 31)
    monkeypatch.undo()
    entorno.servicio.consultar(TITULAR, POLIZA)  # la consulta lo reintenta
    assert entorno.polizas.obtener(POLIZA).fecha_fin == date(2027, 12, 31)


def test_aplicar_dos_veces_el_mismo_pago_renueva_una_sola_vez() -> None:
    entorno = crear_entorno()
    renovacion, _ = entorno.servicio.iniciar(TITULAR, POLIZA)
    pago = entorno.pagar(renovacion.cotizacion_id)
    aplicada = entorno.renovaciones.obtener(NUEVO_ID)

    entorno.servicio.aplicar_pago(pago)
    entorno.servicio.aplicar_pago(pago)

    assert entorno.renovaciones.obtener(NUEVO_ID) == aplicada
    assert entorno.polizas.obtener(POLIZA).fecha_fin == date(2027, 12, 31)


def test_un_pago_que_no_es_de_una_renovacion_se_ignora() -> None:
    entorno = crear_entorno()
    cotizacion_original = entorno.cotizaciones.obtener(COTIZACION)
    entorno.cotizaciones.guardar(
        cotizacion_original.model_copy(
            update={"estado": EstadoCotizacion.VIGENTE, "vigente_hasta": AHORA + timedelta(days=1)}
        )
    )

    entorno.pagar(COTIZACION)

    assert entorno.polizas.obtener(POLIZA).fecha_fin == date(2026, 12, 31)
    assert entorno.renovaciones.por_poliza(POLIZA) == []


def test_si_la_poliza_se_cancela_antes_del_pago_no_se_aplica_y_queda_registrado() -> None:
    entorno = crear_entorno()
    renovacion, _ = entorno.servicio.iniciar(TITULAR, POLIZA)
    cancelada = entorno.polizas.obtener(POLIZA).model_copy(
        update={"estado": EstadoRegistroPoliza.CANCELADA, "cancelada_en": AHORA}
    )
    entorno.polizas.guardar(cancelada)

    pago = entorno.pagar(renovacion.cotizacion_id)

    poliza = entorno.polizas.obtener(POLIZA)
    assert poliza.estado is EstadoRegistroPoliza.CANCELADA and poliza.fecha_fin == date(
        2026, 12, 31
    )
    registro = entorno.renovaciones.obtener(NUEVO_ID)
    assert registro.estado is EstadoRenovacion.NO_APLICADA
    assert registro.pago_id == pago.pago_id
    assert "canceló" in registro.motivo_no_aplicada


def test_la_renovacion_se_consulta_por_su_identificador() -> None:
    entorno = crear_entorno()
    renovacion, _ = entorno.servicio.iniciar(TITULAR, POLIZA)

    assert entorno.servicio.obtener(TITULAR, POLIZA, renovacion.renovacion_id) == renovacion
    with pytest.raises(RenovacionNoEncontrada):
        entorno.servicio.obtener(TITULAR, POLIZA, "REN-NO-EXISTE")


# --- Quién puede renovar ------------------------------------------------------------------


def test_una_poliza_ajena_se_trata_como_inexistente() -> None:
    entorno = crear_entorno()
    otro = Solicitante("CLI-OTRO", Rol.CLIENTE)

    for operacion in (
        lambda: entorno.servicio.consultar(otro, POLIZA),
        lambda: entorno.servicio.iniciar(otro, POLIZA),
        lambda: entorno.servicio.obtener(otro, POLIZA, NUEVO_ID),
    ):
        with pytest.raises(PolizaNoEncontrada):
            operacion()
    assert entorno.renovaciones.por_poliza(POLIZA) == []


def test_el_asesor_renueva_la_poliza_de_su_venta_asistida() -> None:
    entorno = crear_entorno(asesor_id="ASE-1")

    renovacion, creada = entorno.servicio.iniciar(ASESOR, POLIZA)

    assert creada is True
    assert (renovacion.solicitado_por, renovacion.rol_solicitante) == ("ASE-1", "ASESOR_VENTAS")
    cotizacion = entorno.cotizaciones.obtener(renovacion.cotizacion_id)
    # La cotización es del cliente (él la paga), con el asesor de la venta.
    assert cotizacion.cliente_id == CLIENTE and cotizacion.asesor_id == "ASE-1"
    entorno.pagar(renovacion.cotizacion_id)
    assert entorno.polizas.obtener(POLIZA).fecha_fin == date(2027, 12, 31)


def test_el_asesor_no_renueva_la_poliza_de_otro_asesor() -> None:
    for asesor_de_la_venta in ("ASE-2", None):
        entorno = crear_entorno(asesor_id=asesor_de_la_venta)

        with pytest.raises(AccesoDenegado):
            entorno.servicio.consultar(ASESOR, POLIZA)
        with pytest.raises(AccesoDenegado):
            entorno.servicio.iniciar(ASESOR, POLIZA)


def test_un_rol_sin_permiso_no_renueva() -> None:
    entorno = crear_entorno()

    with pytest.raises(AccesoDenegado):
        entorno.servicio.iniciar(Solicitante("ANA-1", Rol.ANALISTA_RIESGOS), POLIZA)


def test_el_pago_usa_el_monto_de_la_cotizacion_de_renovacion() -> None:
    entorno = crear_entorno()
    renovacion, _ = entorno.servicio.iniciar(TITULAR, POLIZA)

    solicitud = solicitud_pago(renovacion.cotizacion_id)
    pago, _ = entorno.pagos_servicio.pagar(CLIENTE, "llave-monto-1", solicitud)

    assert pago.monto == renovacion.prima_total == PRIMA_RENOVADA
    assert pago.cotizacion_id == renovacion.cotizacion_id
    assert DATOS_VIDA["meses_cobertura"] == 12
