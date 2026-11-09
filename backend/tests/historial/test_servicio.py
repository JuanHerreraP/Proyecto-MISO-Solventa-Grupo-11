"""Pruebas del servicio de historial de la póliza (HU25)."""

from decimal import Decimal

import pytest

from app.desembolsos.modelos import EstadoDesembolso
from app.desembolsos.repositorio import RepositorioDesembolsosEnMemoria
from app.pagos.repositorio import RepositorioPagosEnMemoria
from app.polizas.dominio.modelos import EstadoRegistroPoliza
from app.polizas.historial import (
    AccesoDenegadoHistorial,
    PolizaNoEncontrada,
    ServicioHistorialPoliza,
)
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from app.polizas.repositorio_endosos import RepositorioEndososEnMemoria
from app.polizas.vistas_historial import (
    CategoriaMovimiento,
    NaturalezaMonto,
    TipoMovimiento,
)
from tests.historial.fabrica import CLIENTE, POLIZA, desembolso, endoso, pago, poliza


def _servicio(
    *,
    la_poliza=None,
    pagos=(),
    endosos=(),
    desembolsos=(),
) -> ServicioHistorialPoliza:
    repo_polizas = RepositorioPolizasEnMemoria()
    repo_polizas.guardar(la_poliza if la_poliza is not None else poliza())
    repo_pagos = RepositorioPagosEnMemoria()
    for p in pagos:
        repo_pagos.crear(p)
    repo_endosos = RepositorioEndososEnMemoria(repo_polizas)
    for e in endosos:
        repo_endosos.registrar(e, repo_polizas.obtener(e.poliza_id))
    repo_desembolsos = RepositorioDesembolsosEnMemoria()
    for d in desembolsos:
        repo_desembolsos.crear(d)
    return ServicioHistorialPoliza(repo_polizas, repo_pagos, repo_endosos, repo_desembolsos)


def test_incluye_emision_como_unico_movimiento_cuando_no_hay_mas() -> None:
    servicio = _servicio()
    historial = servicio.consultar(POLIZA, CLIENTE)

    assert historial.poliza_id == POLIZA
    assert historial.numero_poliza == "SOLV-VIA-2026-00152"
    assert [m.tipo for m in historial.movimientos] == [TipoMovimiento.EMISION]
    emision = historial.movimientos[0]
    assert emision.categoria is CategoriaMovimiento.POLIZA
    assert emision.monto is None
    assert emision.moneda is None
    assert emision.estado == "COMPLETADO"


def test_incluye_pago_inicial_con_referencia_externa() -> None:
    servicio = _servicio(pagos=[pago()])
    historial = servicio.consultar(POLIZA, CLIENTE)

    financiero = next(
        m for m in historial.movimientos if m.tipo is TipoMovimiento.PAGO_PRIMA_INICIAL
    )
    assert financiero.categoria is CategoriaMovimiento.FINANCIERO
    assert financiero.referencia == "PAY-001"
    assert financiero.referencia_externa == "PSP-88910"
    assert financiero.monto == Decimal("125000.00")
    assert financiero.moneda == "COP"
    assert financiero.estado == "APROBADO"
    assert financiero.naturaleza_monto is NaturalezaMonto.COBRO


def test_pago_sin_referencia_externa_no_inventa_una() -> None:
    servicio = _servicio(pagos=[pago(referencia_pasarela=None)])
    historial = servicio.consultar(POLIZA, CLIENTE)

    financiero = next(
        m for m in historial.movimientos if m.tipo is TipoMovimiento.PAGO_PRIMA_INICIAL
    )
    assert financiero.referencia_externa is None


def test_incluye_endoso_con_linaje_y_consentimiento() -> None:
    servicio = _servicio(endosos=[endoso()])
    historial = servicio.consultar(POLIZA, CLIENTE)

    mov = next(m for m in historial.movimientos if m.tipo is TipoMovimiento.ENDOSO)
    assert mov.categoria is CategoriaMovimiento.CONTRACTUAL
    assert mov.descripcion == "Endoso #2"
    assert mov.monto == Decimal("25000.00")
    assert mov.naturaleza_monto is NaturalezaMonto.AJUSTE
    # Linaje antes/después conservado.
    cambio = mov.cambios[0]
    assert cambio.tipo == "COBERTURA_INCLUIDA"
    assert cambio.antes is None
    assert cambio.despues == {
        "codigo": "EQUIPAJE",
        "nombre": "Pérdida de equipaje",
        "suma_asegurada": "5000000.00",
    }
    # Consentimiento explícito.
    assert mov.consentimiento is not None
    assert mov.consentimiento.explicito is True
    assert mov.consentimiento.tipo == "CONFIRMACION_ENDOSO"
    assert mov.consentimiento.usuario_id == "USR-1"
    assert mov.consentimiento.rol == "CLIENTE"


def test_endoso_sin_ajuste_no_reporta_monto() -> None:
    servicio = _servicio(
        endosos=[endoso(ajuste_prima=Decimal("0.00"), prima_nueva=Decimal("125000.00"))]
    )
    historial = servicio.consultar(POLIZA, CLIENTE)

    mov = next(m for m in historial.movimientos if m.tipo is TipoMovimiento.ENDOSO)
    assert mov.monto is None
    assert mov.naturaleza_monto is None


def test_incluye_desembolso_como_indemnizacion() -> None:
    servicio = _servicio(desembolsos=[desembolso()])
    historial = servicio.consultar(POLIZA, CLIENTE)

    mov = next(
        m for m in historial.movimientos if m.tipo is TipoMovimiento.DESEMBOLSO_INDEMNIZACION
    )
    assert mov.categoria is CategoriaMovimiento.FINANCIERO
    assert mov.monto == Decimal("850000.00")
    assert mov.referencia_externa == "TRF-889900"
    assert mov.naturaleza_monto is NaturalezaMonto.INDEMNIZACION
    assert mov.estado == "COMPLETADA"


def test_excluye_desembolso_fallido() -> None:
    servicio = _servicio(desembolsos=[desembolso(estado=EstadoDesembolso.FALLIDA)])
    historial = servicio.consultar(POLIZA, CLIENTE)

    assert all(m.tipo is not TipoMovimiento.DESEMBOLSO_INDEMNIZACION for m in historial.movimientos)


def test_incluye_cancelacion_cuando_la_poliza_esta_cancelada() -> None:
    servicio = _servicio(la_poliza=poliza(estado=EstadoRegistroPoliza.CANCELADA))
    historial = servicio.consultar(POLIZA, CLIENTE)

    mov = next(m for m in historial.movimientos if m.tipo is TipoMovimiento.CANCELACION)
    assert mov.categoria is CategoriaMovimiento.CONTRACTUAL
    assert mov.estado == "COMPLETADO"


def test_ordena_del_mas_reciente_al_mas_antiguo() -> None:
    servicio = _servicio(pagos=[pago()], endosos=[endoso()], desembolsos=[desembolso()])
    historial = servicio.consultar(POLIZA, CLIENTE)

    tipos = [m.tipo for m in historial.movimientos]
    # 07 nov desembolso, 04 nov endoso, 20 oct 13:45 pago, 20 oct 14:05 emisión.
    assert tipos == [
        TipoMovimiento.DESEMBOLSO_INDEMNIZACION,
        TipoMovimiento.ENDOSO,
        TipoMovimiento.EMISION,
        TipoMovimiento.PAGO_PRIMA_INICIAL,
    ]
    fechas = [m.fecha for m in historial.movimientos]
    assert fechas == sorted(fechas, reverse=True)


def test_no_duplica_movimientos() -> None:
    servicio = _servicio(pagos=[pago()], endosos=[endoso()], desembolsos=[desembolso()])
    historial = servicio.consultar(POLIZA, CLIENTE)

    ids = [m.movimiento_id for m in historial.movimientos]
    assert len(ids) == len(set(ids))


def test_poliza_sin_cotizacion_no_busca_pagos() -> None:
    servicio = _servicio(la_poliza=poliza(cotizacion_id=None), pagos=[pago()])
    historial = servicio.consultar(POLIZA, CLIENTE)

    assert all(m.tipo is not TipoMovimiento.PAGO_PRIMA_INICIAL for m in historial.movimientos)


def test_poliza_inexistente_lanza_excepcion() -> None:
    servicio = _servicio()
    with pytest.raises(PolizaNoEncontrada):
        servicio.consultar("POL-404", CLIENTE)


def test_poliza_de_otro_cliente_lanza_acceso_denegado() -> None:
    servicio = _servicio()
    with pytest.raises(AccesoDenegadoHistorial):
        servicio.consultar(POLIZA, "OTRO-CLIENTE")


def test_rol_interno_consulta_cualquier_poliza() -> None:
    servicio = _servicio()
    # cliente_id=None representa un rol interno de solo lectura.
    historial = servicio.consultar(POLIZA, None)
    assert historial.poliza_id == POLIZA


def test_respuesta_incluye_metadatos_de_la_poliza() -> None:
    servicio = _servicio()
    historial = servicio.consultar(POLIZA, CLIENTE)
    assert historial.cliente_id == CLIENTE
    assert historial.nombre_ramo == "Seguro de viaje"
    assert historial.estado in {"VIGENTE", "VENCIDA", "CANCELADA"}


def test_vista_de_auditoria_agrega_ajuste_y_datos_tecnicos_del_endoso() -> None:
    servicio = _servicio(endosos=[endoso()])
    historial = servicio.consultar(POLIZA, None, incluir_auditoria=True)

    mov = next(m for m in historial.movimientos if m.tipo is TipoMovimiento.ENDOSO)
    assert mov.auditoria is not None
    assert mov.auditoria.ip_solicitante == "10.0.0.1"
    assert mov.auditoria.user_agent == "pruebas"
    assert mov.ajuste_prima is not None
    assert mov.ajuste_prima.prima_anterior == Decimal("125000.00")
    assert mov.ajuste_prima.ajuste == Decimal("25000.00")
    assert mov.ajuste_prima.prima_nueva == Decimal("150000.00")


def test_sin_vista_de_auditoria_no_expone_datos_tecnicos() -> None:
    servicio = _servicio(endosos=[endoso()])
    historial = servicio.consultar(POLIZA, CLIENTE)

    mov = next(m for m in historial.movimientos if m.tipo is TipoMovimiento.ENDOSO)
    assert mov.auditoria is None
    assert mov.ajuste_prima is None
