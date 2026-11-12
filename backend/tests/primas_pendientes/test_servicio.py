"""Primas pendientes del cliente: renovaciones, cotizaciones y firmas pendientes (HU21)."""

from datetime import date
from decimal import Decimal

from app.cotizaciones.dominio.modelos import EstadoCotizacion
from app.firmas.modelos import EstadoFirma
from app.polizas.dominio.modelos import EstadoRegistroPoliza
from app.polizas.dominio.primas_pendientes import (
    MENSAJE_FIRMA_PENDIENTE,
    AccionPrima,
    TipoPrimaPendiente,
    fin_de_vigencia,
)
from app.polizas.primas_pendientes import ServicioPrimasPendientes
from tests.primas_pendientes.fabrica import (
    AHORA,
    CLIENTE,
    COTIZACION,
    POLIZA,
    cotizacion_vigente,
    crear_entorno_primas,
    pago_aprobado,
)


def test_sin_nada_pendiente_la_lista_esta_vacia() -> None:
    e = crear_entorno_primas()

    resultado = e.listar()

    assert resultado.primas == ()
    assert resultado.total == 0


def test_una_renovacion_sin_pagar_aparece_con_poliza_valor_y_fecha_limite() -> None:
    e = crear_entorno_primas()
    renovacion = e.iniciar_renovacion()

    resultado = e.listar()

    assert resultado.total == 1
    prima = resultado.primas[0]
    assert prima.tipo is TipoPrimaPendiente.RENOVACION
    assert prima.accion is AccionPrima.PAGAR
    assert prima.referencia_id == renovacion.renovacion_id
    assert prima.cotizacion_id == renovacion.cotizacion_id
    assert prima.poliza_id == POLIZA
    assert prima.numero_poliza == "SOL-2026-VIDA0001"
    assert prima.nombre_ramo == "Microseguro de vida"
    assert prima.monto == Decimal("420000.00") and prima.moneda == "COP"
    assert prima.fecha_limite == renovacion.vigente_hasta
    assert prima.mensaje is None


def test_la_fecha_limite_no_pasa_del_fin_de_la_poliza() -> None:
    e = crear_entorno_primas()
    e.base.reloj.avanzar(days=18)  # 28 de diciembre: la cotización duraría hasta el 4 de enero
    renovacion = e.iniciar_renovacion()

    prima = e.listar().primas[0]

    assert renovacion.vigente_hasta > fin_de_vigencia(date(2026, 12, 31))
    assert prima.fecha_limite == fin_de_vigencia(date(2026, 12, 31))


def test_una_renovacion_pagada_ya_no_aparece() -> None:
    e = crear_entorno_primas()
    renovacion = e.iniciar_renovacion()

    e.base.pagar(renovacion.cotizacion_id)

    assert e.listar().primas == ()


def test_si_el_aviso_del_pago_fallo_se_aplica_la_renovacion_y_no_se_lista() -> None:
    e = crear_entorno_primas(avisar_pagos=False)
    renovacion = e.iniciar_renovacion()
    e.base.pagar(renovacion.cotizacion_id)
    assert e.base.polizas.obtener(POLIZA).fecha_fin == date(2026, 12, 31)

    assert e.listar().primas == ()

    assert e.base.polizas.obtener(POLIZA).fecha_fin == date(2027, 12, 31)


def test_una_renovacion_con_la_cotizacion_vencida_no_aparece() -> None:
    e = crear_entorno_primas()
    e.iniciar_renovacion()

    e.base.reloj.avanzar(days=8)

    assert e.listar().primas == ()


def test_la_renovacion_de_una_poliza_cancelada_no_aparece() -> None:
    e = crear_entorno_primas()
    e.iniciar_renovacion()
    poliza = e.base.polizas.obtener(POLIZA)
    e.base.polizas.guardar(
        poliza.model_copy(update={"estado": EstadoRegistroPoliza.CANCELADA, "cancelada_en": AHORA})
    )

    assert e.listar().primas == ()


def test_una_cotizacion_vigente_sin_pagar_aparece_con_ramo_y_numero_de_cotizacion() -> None:
    e = crear_entorno_primas()
    nueva = cotizacion_vigente()
    e.base.cotizaciones.guardar(nueva)

    resultado = e.listar()

    assert resultado.total == 1
    prima = resultado.primas[0]
    assert prima.tipo is TipoPrimaPendiente.COTIZACION
    assert prima.accion is AccionPrima.PAGAR
    assert prima.referencia_id == prima.cotizacion_id == "COT-NUEVA"
    assert prima.poliza_id is None and prima.numero_poliza is None
    assert prima.nombre_ramo == "Microseguro de vida"
    assert prima.monto == Decimal("89000.00")
    assert prima.fecha_limite == nueva.vigente_hasta


def test_una_cotizacion_vencida_o_en_borrador_no_aparece() -> None:
    e = crear_entorno_primas()
    e.base.cotizaciones.guardar(cotizacion_vigente("COT-VENCIDA", vigente_dias=1))
    e.base.reloj.avanzar(days=2)
    borrador = cotizacion_vigente("COT-BORRADOR", estado=EstadoCotizacion.BORRADOR).model_copy(
        update={"prima_total": None, "cobertura_principal": None, "vigente_hasta": None}
    )
    e.base.cotizaciones.guardar(borrador)

    assert e.listar().primas == ()


def test_la_cotizacion_de_una_renovacion_no_se_repite_como_cotizacion() -> None:
    e = crear_entorno_primas()
    renovacion = e.iniciar_renovacion()

    primas = e.listar().primas

    assert [p.tipo for p in primas] == [TipoPrimaPendiente.RENOVACION]
    assert [p.cotizacion_id for p in primas] == [renovacion.cotizacion_id]


def test_una_cotizacion_pagada_sin_poliza_avisa_que_falta_firmar() -> None:
    e = crear_entorno_primas()
    e.base.pagos.crear(pago_aprobado("COT-NUEVA"))
    e.base.cotizaciones.guardar(cotizacion_vigente(estado=EstadoCotizacion.ACEPTADA))

    resultado = e.listar()

    assert resultado.total == 1
    prima = resultado.primas[0]
    assert prima.tipo is TipoPrimaPendiente.FIRMA_PENDIENTE
    assert prima.accion is AccionPrima.FIRMAR
    assert prima.cotizacion_id == "COT-NUEVA"
    assert prima.monto == Decimal("89000.00")  # lo que ya pagó
    assert prima.fecha_limite is None
    assert prima.mensaje == MENSAJE_FIRMA_PENDIENTE


def test_si_ya_firmo_no_se_le_pide_firmar() -> None:
    e = crear_entorno_primas()
    e.base.pagos.crear(pago_aprobado("COT-NUEVA"))
    e.base.cotizaciones.guardar(cotizacion_vigente(estado=EstadoCotizacion.ACEPTADA))
    e.firmas.firmar("COT-NUEVA", EstadoFirma.FIRMADA)

    assert e.listar().primas == ()


def test_una_firma_bloqueada_sigue_pendiente() -> None:
    e = crear_entorno_primas()
    e.base.pagos.crear(pago_aprobado("COT-NUEVA"))
    e.base.cotizaciones.guardar(cotizacion_vigente(estado=EstadoCotizacion.ACEPTADA))
    e.firmas.firmar("COT-NUEVA", EstadoFirma.BLOQUEADA)

    assert [p.tipo for p in e.listar().primas] == [TipoPrimaPendiente.FIRMA_PENDIENTE]


def test_una_cotizacion_pagada_con_poliza_emitida_no_aparece() -> None:
    e = crear_entorno_primas()
    e.base.pagos.crear(pago_aprobado(COTIZACION))  # la cotización de la póliza de la fábrica

    assert e.listar().primas == ()


def test_no_aparece_lo_de_otro_cliente() -> None:
    e = crear_entorno_primas()
    e.base.cotizaciones.guardar(cotizacion_vigente("COT-AJENA", cliente_id="CLI-OTRO"))
    e.iniciar_renovacion()

    assert e.listar("CLI-OTRO").total == 1  # solo su cotización
    assert [p.cotizacion_id for p in e.listar("CLI-OTRO").primas] == ["COT-AJENA"]
    assert [p.tipo for p in e.listar(CLIENTE).primas] == [TipoPrimaPendiente.RENOVACION]
    assert e.listar("CLI-SIN-NADA").primas == ()


def test_las_mas_urgentes_van_primero_y_las_firmas_al_final() -> None:
    e = crear_entorno_primas()
    e.base.cotizaciones.guardar(cotizacion_vigente("COT-LEJANA", vigente_dias=6))
    e.base.cotizaciones.guardar(cotizacion_vigente("COT-CERCANA", vigente_dias=2))
    e.base.pagos.crear(pago_aprobado("COT-PAGADA"))
    e.base.cotizaciones.guardar(cotizacion_vigente("COT-PAGADA", estado=EstadoCotizacion.ACEPTADA))

    primas = e.listar().primas

    assert [p.cotizacion_id for p in primas] == ["COT-CERCANA", "COT-LEJANA", "COT-PAGADA"]
    assert primas[0].fecha_limite < primas[1].fecha_limite
    assert primas[2].fecha_limite is None


def test_el_fin_de_vigencia_es_la_medianoche_de_bogota_del_dia_siguiente() -> None:
    limite = fin_de_vigencia(date(2026, 12, 31))

    assert limite.isoformat() == "2027-01-01T00:00:00-05:00"


def test_una_renovacion_sin_su_cotizacion_no_se_lista() -> None:
    e = crear_entorno_primas()
    renovacion = e.iniciar_renovacion()
    e.base.cotizaciones._por_id.pop(renovacion.cotizacion_id)

    assert e.listar().primas == ()


def test_si_no_se_puede_aplicar_el_pago_la_lista_igual_responde() -> None:
    e = crear_entorno_primas(avisar_pagos=False)
    renovacion = e.iniciar_renovacion()
    e.base.pagar(renovacion.cotizacion_id)

    def falla(pago):
        raise RuntimeError("base de datos caída")

    for aplicar in (falla, None):
        servicio = ServicioPrimasPendientes(
            cotizaciones=e.base.cotizaciones,
            pagos=e.base.pagos,
            polizas=e.base.polizas,
            renovaciones=e.base.renovaciones,
            firmas=e.firmas,
            aplicar_pago=aplicar,
            reloj=e.base.reloj,
        )

        assert servicio.listar(CLIENTE).primas == ()
