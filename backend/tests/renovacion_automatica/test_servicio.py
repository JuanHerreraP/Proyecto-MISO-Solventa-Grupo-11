"""Renovación automática: preaviso, cobro con la tarjeta registrada y contrato (HU17)."""

import hashlib
import json
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.identidad.modelos import Rol
from app.pagos.modelos import EstadoPago
from app.pagos.servicio import firmar
from app.polizas.dominio.modelos import EstadoRegistroPoliza, RamoPoliza
from app.polizas.dominio.renovacion import EstadoRenovacion, RenovacionNoEncontrada
from app.polizas.dominio.renovacion_automatica import (
    EstadoCicloRenovacion,
    MedioPagoRegistrado,
)
from app.polizas.emision import AccesoDenegado, DocumentoAlterado
from app.polizas.endosos import Solicitante
from app.polizas.renovacion_automatica import RenovacionAutomaticaNoDisponible
from app.polizas.servicio import PolizaNoEncontrada
from tests.renovacion_automatica.fabrica import (
    CAIDA,
    CORREO,
    INICIO_PREAVISO,
    POLIZA,
    RECHAZADA,
    TARJETA,
    TITULAR,
    VENCIMIENTO,
    crear_entorno_automatico,
)
from tests.renovaciones.fabrica import ASESOR, CLIENTE, PRIMA_RENOVADA

NUEVO_FIN = date(2027, 12, 31)


def pagos_de(e) -> list:
    return e.base.pagos.listar_de_cliente(CLIENTE)


# --- Criterio 1: alerta de vencimiento ----------------------------------------------------


def test_30_dias_antes_envia_el_preaviso_con_la_prima_recalculada() -> None:
    e = crear_entorno_automatico()
    e.registrar(TARJETA)

    resultado = e.ejecutar_el(INICIO_PREAVISO)

    assert resultado.revisadas == 1 and resultado.preavisos == 1
    [correo] = e.correo.preavisos
    assert correo.destinatario == CORREO
    assert correo.numero_poliza == "SOL-2026-VIDA0001"
    assert correo.vence_el == VENCIMIENTO
    assert (correo.nuevo_inicio, correo.nuevo_fin) == (date(2027, 1, 1), NUEVO_FIN)
    assert correo.prima_actual == Decimal("150000.00")
    assert correo.prima_renovacion == PRIMA_RENOVADA
    assert correo.renovacion_automatica_activa is True
    assert correo.tarjeta_ultimos_digitos == "4242"
    ciclo = e.ciclo()
    assert ciclo.estado is EstadoCicloRenovacion.PREAVISADA
    assert ciclo.prima_avisada == PRIMA_RENOVADA and ciclo.vence_el == VENCIMIENTO


def test_el_preaviso_se_envia_una_sola_vez_por_periodo() -> None:
    e = crear_entorno_automatico()

    e.ejecutar_el(INICIO_PREAVISO)
    e.ejecutar_el(INICIO_PREAVISO)
    segunda = e.ejecutar_el(date(2026, 12, 15))

    assert len(e.correo.preavisos) == 1
    assert segunda.preavisos == 0
    assert pagos_de(e) == []  # Antes del vencimiento no se cobra nada.


def test_antes_de_la_ventana_no_se_avisa_nada() -> None:
    e = crear_entorno_automatico()

    resultado = e.ejecutar_el(date(2026, 11, 30))

    assert resultado.revisadas == 0
    assert e.correo.preavisos == [] and e.ciclo() is None


def test_el_preaviso_dice_si_la_renovacion_automatica_esta_desactivada() -> None:
    e = crear_entorno_automatico()
    e.registrar(medio=None, activa=False)

    e.ejecutar_el(INICIO_PREAVISO)

    [correo] = e.correo.preavisos
    assert correo.renovacion_automatica_activa is False
    assert correo.tarjeta_ultimos_digitos is None


def test_sin_correo_no_marca_el_preaviso_y_lo_reintenta() -> None:
    e = crear_entorno_automatico(con_correo=False)

    e.ejecutar_el(INICIO_PREAVISO)
    assert e.correo.preavisos == []
    assert e.ciclo().preaviso_enviado_en is None

    e.directorio.correos[CLIENTE] = CORREO
    e.ejecutar_el(date(2026, 12, 2))

    assert len(e.correo.preavisos) == 1


def test_una_poliza_sin_datos_de_riesgo_queda_como_no_renovable_sin_preaviso() -> None:
    e = crear_entorno_automatico(con_cotizacion=False)
    e.registrar(TARJETA)

    resultado = e.ejecutar_el(INICIO_PREAVISO)
    e.ejecutar_el(VENCIMIENTO)

    assert resultado.no_renovables == 1
    assert e.correo.preavisos == []
    assert e.ciclo().estado is EstadoCicloRenovacion.NO_RENOVABLE
    assert pagos_de(e) == []


@pytest.mark.parametrize(
    "cambios",
    [
        {"ramo": RamoPoliza.VIAJE},
        {"estado": EstadoRegistroPoliza.CANCELADA, "cancelada_en": "2026-06-01T15:00:00Z"},
    ],
    ids=["ramo-que-no-se-renueva", "cancelada"],
)
def test_las_polizas_que_no_se_renuevan_se_ignoran(cambios) -> None:
    e = crear_entorno_automatico(**cambios)
    e.registrar(TARJETA)

    e.ejecutar_el(INICIO_PREAVISO)
    resultado = e.ejecutar_el(VENCIMIENTO)

    assert resultado.revisadas == 0
    assert e.correo.preavisos == [] and pagos_de(e) == []


# --- Criterios 2 y 3: cobro, renovación y contrato ----------------------------------------


def test_el_dia_del_vencimiento_cobra_renueva_y_envia_el_contrato() -> None:
    e = crear_entorno_automatico()
    e.registrar(TARJETA)
    e.ejecutar_el(INICIO_PREAVISO)

    resultado = e.ejecutar_el(VENCIMIENTO)

    assert resultado.renovadas == 1 and resultado.contratos_enviados == 1
    poliza = e.poliza()
    assert (poliza.fecha_inicio, poliza.fecha_fin) == (date(2027, 1, 1), NUEVO_FIN)
    assert poliza.prima_total == PRIMA_RENOVADA

    [pago] = pagos_de(e)
    assert pago.estado is EstadoPago.APROBADO and pago.monto == PRIMA_RENOVADA

    ciclo = e.ciclo()
    assert ciclo.estado is EstadoCicloRenovacion.RENOVADA
    assert ciclo.pago_id == pago.pago_id and ciclo.intentos_cobro == 1
    renovacion = e.base.renovaciones.obtener(ciclo.renovacion_id)
    assert renovacion.estado is EstadoRenovacion.APLICADA
    assert renovacion.rol_solicitante == Rol.SERVICIO_INTERNO.value

    contenido = e.almacen.leer(ciclo.clave_documento)
    assert contenido.startswith(b"%PDF")
    assert hashlib.sha256(contenido).hexdigest() == ciclo.huella_documento

    [correo] = e.correo.renovaciones
    assert correo.destinatario == CORREO
    assert (correo.nuevo_inicio, correo.nuevo_fin) == (date(2027, 1, 1), NUEVO_FIN)
    assert correo.prima_total == PRIMA_RENOVADA
    assert correo.adjunto_pdf == contenido
    assert correo.nombre_adjunto == "renovacion-SOL-2026-VIDA0001-20261231.pdf"
    assert ciclo.contrato_enviado_en is not None


def test_si_la_tarea_no_corrio_antes_preavisa_y_cobra_el_mismo_dia() -> None:
    e = crear_entorno_automatico()
    e.registrar(TARJETA)

    resultado = e.ejecutar_el(VENCIMIENTO)

    assert resultado.preavisos == 1 and resultado.renovadas == 1
    assert e.poliza().fecha_fin == NUEVO_FIN


def test_ejecutar_dos_veces_no_cobra_ni_envia_dos_veces() -> None:
    e = crear_entorno_automatico()
    e.registrar(TARJETA)
    e.ejecutar_el(VENCIMIENTO)

    segunda = e.ejecutar_el(VENCIMIENTO)
    e.ejecutar_el(date(2027, 1, 1))

    assert len(pagos_de(e)) == 1
    assert len(e.correo.renovaciones) == 1 and len(e.correo.preavisos) == 1
    assert segunda.renovadas == 0 and segunda.contratos_enviados == 0
    assert e.poliza().fecha_fin == NUEVO_FIN


def test_desactivada_no_cobra_ni_renueva() -> None:
    e = crear_entorno_automatico()
    e.registrar(TARJETA, activa=False)

    resultado = e.ejecutar_el(VENCIMIENTO)

    assert resultado.desactivadas == 1
    assert pagos_de(e) == []
    assert e.poliza().fecha_fin == VENCIMIENTO
    assert e.ciclo().estado is EstadoCicloRenovacion.DESACTIVADA
    assert e.base.renovaciones.por_poliza(POLIZA) == []


def test_reactivarla_el_mismo_dia_del_vencimiento_la_cobra() -> None:
    e = crear_entorno_automatico()
    e.registrar(TARJETA, activa=False)
    e.ejecutar_el(VENCIMIENTO)

    e.registrar(TARJETA, activa=True)
    e.ejecutar_el(VENCIMIENTO)

    assert e.ciclo().estado is EstadoCicloRenovacion.RENOVADA
    assert e.poliza().fecha_fin == NUEVO_FIN


def test_sin_tarjeta_deja_la_renovacion_para_pagar_a_mano_y_avisa() -> None:
    e = crear_entorno_automatico()

    resultado = e.ejecutar_el(VENCIMIENTO)

    assert resultado.sin_medio_de_pago == 1
    ciclo = e.ciclo()
    assert ciclo.estado is EstadoCicloRenovacion.SIN_MEDIO_DE_PAGO
    renovacion = e.base.renovaciones.obtener(ciclo.renovacion_id)
    assert renovacion.estado is EstadoRenovacion.PENDIENTE_PAGO
    [aviso] = e.correo.no_realizadas
    assert aviso.destinatario == CORREO and aviso.pagar_hasta == renovacion.vigente_hasta
    assert pagos_de(e) == []

    e.ejecutar_el(VENCIMIENTO)
    assert len(e.correo.no_realizadas) == 1  # El aviso no se repite.


def test_si_registra_la_tarjeta_despues_del_vencimiento_se_cobra_al_dia_siguiente() -> None:
    e = crear_entorno_automatico()
    e.ejecutar_el(VENCIMIENTO)

    e.registrar(TARJETA)
    resultado = e.ejecutar_el(date(2027, 1, 1))

    assert resultado.renovadas == 1 and resultado.contratos_enviados == 1
    assert e.poliza().fecha_fin == NUEVO_FIN
    assert e.ciclo().estado is EstadoCicloRenovacion.RENOVADA


def test_si_el_cliente_paga_a_mano_tras_el_aviso_se_le_envia_el_contrato() -> None:
    e = crear_entorno_automatico()
    e.ejecutar_el(VENCIMIENTO)
    renovacion = e.base.renovaciones.obtener(e.ciclo().renovacion_id)

    e.base.pagar(renovacion.cotizacion_id, llave="pago-manual-1")
    e.ejecutar_el(date(2027, 1, 1))

    assert e.ciclo().estado is EstadoCicloRenovacion.RENOVADA
    assert len(e.correo.renovaciones) == 1


def test_tarjeta_rechazada_avisa_y_no_reintenta_con_la_misma_tarjeta() -> None:
    e = crear_entorno_automatico()
    e.registrar(RECHAZADA)

    resultado = e.ejecutar_el(VENCIMIENTO)
    e.ejecutar_el(VENCIMIENTO)
    e.ejecutar_el(date(2027, 1, 1))

    assert resultado.rechazadas == 1
    ciclo = e.ciclo()
    assert ciclo.estado is EstadoCicloRenovacion.COBRO_RECHAZADO
    assert "FONDOS_INSUFICIENTES" in ciclo.motivo
    assert len(pagos_de(e)) == 1 and ciclo.intentos_cobro == 1
    assert len(e.correo.no_realizadas) == 1
    assert e.poliza().fecha_fin == VENCIMIENTO


def test_tras_un_rechazo_una_tarjeta_nueva_se_cobra_y_renueva() -> None:
    e = crear_entorno_automatico()
    e.registrar(RECHAZADA)
    e.ejecutar_el(VENCIMIENTO)

    e.registrar(TARJETA)
    e.ejecutar_el(date(2027, 1, 1))

    ciclo = e.ciclo()
    assert ciclo.estado is EstadoCicloRenovacion.RENOVADA and ciclo.intentos_cobro == 2
    estados = sorted(p.estado.value for p in pagos_de(e))
    assert estados == ["APROBADO", "RECHAZADO"]
    assert e.poliza().fecha_fin == NUEVO_FIN


def test_si_la_renovacion_vence_sin_pago_el_ciclo_se_cierra() -> None:
    e = crear_entorno_automatico()
    e.ejecutar_el(VENCIMIENTO)

    e.ejecutar_el(date(2027, 1, 8))  # La cotización de la renovación vence a los 7 días.

    assert e.ciclo().estado is EstadoCicloRenovacion.NO_PAGADA
    assert e.servicio._ciclos.abiertos() == []


def test_pasarela_caida_queda_pendiente_y_concluye_al_confirmarse(monkeypatch) -> None:
    monkeypatch.setenv("PAGOS_WEBHOOK_SECRET", "secreto-de-pruebas")
    e = crear_entorno_automatico()
    e.registrar(CAIDA)

    resultado = e.ejecutar_el(VENCIMIENTO)

    assert resultado.pendientes == 1
    ciclo = e.ciclo()
    assert ciclo.estado is EstadoCicloRenovacion.COBRO_PENDIENTE
    [pago] = pagos_de(e)
    assert pago.estado is EstadoPago.PENDIENTE and ciclo.pago_id == pago.pago_id

    referencia = "PSP-" + hashlib.sha256(pago.pago_id.encode()).hexdigest()[:16]
    actual = e.base.pagos.obtener(pago.pago_id)
    e.base.pagos.guardar(actual.model_copy(update={"referencia_pasarela": referencia}))
    cuerpo = json.dumps({"referencia": referencia, "estado": "APROBADO"}).encode()
    e.base.pagos_servicio.confirmar(
        cuerpo, firmar(cuerpo, b"secreto-de-pruebas"), referencia, EstadoPago.APROBADO
    )
    seguimiento = e.ejecutar_el(date(2027, 1, 1))

    assert seguimiento.renovadas == 1 and seguimiento.contratos_enviados == 1
    assert e.ciclo().estado is EstadoCicloRenovacion.RENOVADA
    assert e.poliza().fecha_fin == NUEVO_FIN


def test_si_el_cliente_ya_renovo_a_mano_no_hay_cobro_automatico() -> None:
    e = crear_entorno_automatico()
    e.registrar(TARJETA)
    renovacion, _ = e.base.servicio.iniciar(TITULAR, POLIZA)
    e.base.pagar(renovacion.cotizacion_id)

    resultado = e.ejecutar_el(VENCIMIENTO)

    assert resultado.revisadas == 0
    assert len(pagos_de(e)) == 1


def test_si_el_envio_del_contrato_falla_se_reintenta_en_la_siguiente_ejecucion() -> None:
    e = crear_entorno_automatico()
    e.registrar(TARJETA)
    original = e.correo.enviar_renovacion_emitida

    def caido(_correo):
        raise RuntimeError("SMTP caído")

    e.correo.enviar_renovacion_emitida = caido
    resultado = e.ejecutar_el(VENCIMIENTO)
    assert resultado.renovadas == 1 and resultado.errores == 1
    assert e.ciclo().contrato_enviado_en is None
    assert e.ciclo().huella_documento is not None

    e.correo.enviar_renovacion_emitida = original
    segunda = e.ejecutar_el(date(2027, 1, 1))

    assert segunda.contratos_enviados == 1
    assert len(e.correo.renovaciones) == 1
    assert len(pagos_de(e)) == 1


# --- Preferencia del cliente --------------------------------------------------------------


def test_por_defecto_esta_activa_y_sin_tarjeta() -> None:
    e = crear_entorno_automatico()

    _, preferencia, ciclo = e.servicio.consultar(TITULAR, POLIZA)

    assert preferencia.activa is True and preferencia.medio_pago is None
    assert ciclo is None


def test_el_cliente_registra_la_tarjeta_y_luego_la_quita() -> None:
    e = crear_entorno_automatico()

    registrada = e.servicio.configurar(TITULAR, POLIZA, activa=True, medio_pago=TARJETA)
    assert registrada.medio_pago == TARJETA and registrada.actualizado_por == CLIENTE

    sin_cambio = e.servicio.configurar(TITULAR, POLIZA, activa=False)
    assert sin_cambio.activa is False and sin_cambio.medio_pago == TARJETA

    quitada = e.servicio.configurar(TITULAR, POLIZA, activa=True, quitar_medio_pago=True)
    assert quitada.medio_pago is None


def test_el_asesor_puede_desactivarla_pero_no_registrar_tarjetas() -> None:
    e = crear_entorno_automatico(asesor_id=ASESOR.actor_id)

    desactivada = e.servicio.configurar(ASESOR, POLIZA, activa=False)
    assert desactivada.activa is False

    with pytest.raises(AccesoDenegado):
        e.servicio.configurar(ASESOR, POLIZA, activa=True, medio_pago=TARJETA)


def test_otro_cliente_no_ve_la_poliza() -> None:
    e = crear_entorno_automatico()
    otro = Solicitante("CLI-999", Rol.CLIENTE)

    with pytest.raises(PolizaNoEncontrada):
        e.servicio.consultar(otro, POLIZA)
    with pytest.raises(PolizaNoEncontrada):
        e.servicio.configurar(otro, POLIZA, activa=False)


def test_un_ramo_que_no_se_renueva_no_se_puede_configurar() -> None:
    e = crear_entorno_automatico(ramo=RamoPoliza.VIAJE)

    with pytest.raises(RenovacionAutomaticaNoDisponible):
        e.servicio.configurar(TITULAR, POLIZA, activa=True)


def test_la_tarjeta_nunca_se_acepta_en_claro() -> None:
    with pytest.raises(ValidationError):
        MedioPagoRegistrado(token_tarjeta="4111 1111 1111 1111")
    with pytest.raises(ValidationError):
        MedioPagoRegistrado(token_tarjeta="tok_visa_aprobado", ultimos_digitos="42")


# --- Documento del periodo renovado -------------------------------------------------------


def test_el_cliente_descarga_el_documento_de_la_renovacion() -> None:
    e = crear_entorno_automatico()
    e.registrar(TARJETA)
    e.ejecutar_el(VENCIMIENTO)
    ciclo = e.ciclo()

    documento = e.servicio.documento(TITULAR, POLIZA, ciclo.renovacion_id)

    assert documento.contenido.startswith(b"%PDF")
    assert documento.huella_sha256 == ciclo.huella_documento
    assert documento.nombre_archivo == "renovacion-SOL-2026-VIDA0001-20261231.pdf"


def test_un_documento_inexistente_o_alterado_no_se_entrega() -> None:
    e = crear_entorno_automatico()
    e.registrar(TARJETA)
    e.ejecutar_el(VENCIMIENTO)
    ciclo = e.ciclo()

    with pytest.raises(RenovacionNoEncontrada):
        e.servicio.documento(TITULAR, POLIZA, "REN-OTRA")

    e.almacen._por_clave[ciclo.clave_documento] = b"%PDF alterado"
    with pytest.raises(DocumentoAlterado):
        e.servicio.documento(TITULAR, POLIZA, ciclo.renovacion_id)
