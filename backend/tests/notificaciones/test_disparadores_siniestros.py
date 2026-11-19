"""Disparadores de la evaluación de siniestros: pago paramétrico y cambio de estado."""

from decimal import Decimal

import pytest

from app.notificaciones.canal import EnviadorPushSimulado
from app.notificaciones.modelos import TipoNotificacion
from app.polizas.dominio.modelos import CoberturaPoliza, RamoPoliza
from app.siniestros.evaluacion import ServicioEvaluacion
from app.siniestros.modelos import EstadoSiniestro, OrigenSiniestro
from app.siniestros.telemetria import EventoParametrico, ServicioTelemetria
from tests.billetera.fabrica import poliza
from tests.desembolsos.fabrica import AHORA, CLIENTE, OPERADOR, crear_entorno, siniestro
from tests.notificaciones.fabrica import crear_servicio, dispositivo, preferencia


def entorno(*siniestros, con_notificaciones: bool = True, servicio=None):
    """El entorno de la evaluación, con notificaciones y un teléfono del cliente registrado."""
    e = crear_entorno(*siniestros)
    notificaciones, repos, _ = crear_servicio(enviador=EnviadorPushSimulado())
    enviador = notificaciones._enviador
    repos.dispositivos.guardar(dispositivo("token-1", cliente_id=CLIENTE))
    e.evaluacion = ServicioEvaluacion(
        e.siniestros,
        e.polizas,
        e.desembolsos,
        reloj=lambda: AHORA,
        notificaciones=(servicio or notificaciones) if con_notificaciones else None,
    )
    return e, repos, enviador


def bandeja(repos):
    return repos.notificaciones.listar(CLIENTE)


# --- Cambio de estado ----------------------------------------------------------------------


def test_aprobar_un_siniestro_manual_avisa_al_cliente_con_el_monto() -> None:
    e, repos, enviador = entorno()

    e.evaluacion.aprobar("SIN-1", OPERADOR)

    (n,) = bandeja(repos)
    assert n.tipo is TipoNotificacion.ESTADO_SINIESTRO
    assert n.titulo == "Tu siniestro fue aprobado"
    assert n.cuerpo == "Aprobamos tu siniestro de la póliza SOL-VI-000001 por $850.000 COP."
    assert n.datos["siniestro_id"] == "SIN-1" and n.datos["estado"] == "APROBADO"
    (push,) = enviador.enviados
    assert push.titulo == n.titulo and push.tokens == ("token-1",)
    assert push.datos["siniestro_id"] == "SIN-1"  # al tocarla abre el detalle


def test_rechazar_un_siniestro_avisa_al_cliente() -> None:
    e, repos, enviador = entorno()

    e.evaluacion.rechazar("SIN-1", OPERADOR, "Fuera de cobertura")

    (n,) = bandeja(repos)
    assert n.titulo == "Tu siniestro fue rechazado" and n.datos["estado"] == "RECHAZADO"
    assert len(enviador.enviados) == 1


def test_repetir_la_misma_decision_no_vuelve_a_notificar() -> None:
    e, repos, enviador = entorno()
    e.evaluacion.aprobar("SIN-1", OPERADOR)

    e.evaluacion.aprobar("SIN-1", OPERADOR)
    e.evaluacion.aprobar("SIN-1", OPERADOR, Decimal("850000.00"))

    assert len(bandeja(repos)) == 1 and len(enviador.enviados) == 1


def test_una_decision_que_se_rechaza_no_genera_aviso() -> None:
    from app.siniestros.evaluacion import MontoInvalido, SiniestroYaEvaluado

    e, repos, _ = entorno()
    with pytest.raises(MontoInvalido):
        e.evaluacion.aprobar("SIN-1", OPERADOR, Decimal("999999999.00"))
    e.evaluacion.rechazar("SIN-1", OPERADOR, "No aplica")
    with pytest.raises(SiniestroYaEvaluado):
        e.evaluacion.aprobar("SIN-1", OPERADOR)

    # Solo quedó el aviso del rechazo real.
    assert [n.titulo for n in bandeja(repos)] == ["Tu siniestro fue rechazado"]


def test_el_aviso_va_al_cliente_del_siniestro() -> None:
    e, repos, _ = entorno(siniestro(cliente_id="CLI-OTRO"))

    e.evaluacion.aprobar("SIN-1", OPERADOR)

    assert bandeja(repos) == []
    assert len(repos.notificaciones.listar("CLI-OTRO")) == 1


def test_con_el_push_deshabilitado_la_decision_igual_queda_en_la_bandeja() -> None:
    e, repos, enviador = entorno()
    repos.preferencias.guardar(preferencia(False))

    e.evaluacion.aprobar("SIN-1", OPERADOR)

    assert len(bandeja(repos)) == 1 and enviador.enviados == []


def test_dos_decisiones_el_mismo_dia_se_agrupan_en_un_resumen() -> None:
    e, repos, enviador = entorno(siniestro(siniestro_id="SIN-1"), siniestro(siniestro_id="SIN-2"))

    e.evaluacion.rechazar("SIN-1", OPERADOR, "No aplica")
    e.evaluacion.aprobar("SIN-2", OPERADOR)

    primero, segundo = enviador.enviados
    assert primero.agrupado is False
    assert segundo.agrupado is True
    assert segundo.cuerpo == "Tienes 2 actualizaciones en tus siniestros hoy."
    assert primero.etiqueta == segundo.etiqueta
    assert len(bandeja(repos)) == 2


# --- Aislamiento de fallas -----------------------------------------------------------------


class Caido:
    """Un servicio de notificaciones que siempre falla."""

    def notificar_evento(self, cliente_id, evento):
        raise RuntimeError("base de notificaciones caída")


def test_si_las_notificaciones_fallan_la_aprobacion_sigue_adelante(caplog) -> None:
    e, _, _ = entorno(servicio=Caido())

    aprobado, desembolso = e.evaluacion.aprobar("SIN-1", OPERADOR)

    assert aprobado.estado is EstadoSiniestro.APROBADO
    assert desembolso is not None
    assert e.siniestros.obtener("SIN-1").estado is EstadoSiniestro.APROBADO
    assert "No se pudo notificar la decisión del siniestro SIN-1" in caplog.text


def test_si_las_notificaciones_fallan_el_rechazo_sigue_adelante() -> None:
    e, _, _ = entorno(servicio=Caido())

    rechazado = e.evaluacion.rechazar("SIN-1", OPERADOR, "No aplica")

    assert rechazado.estado is EstadoSiniestro.RECHAZADO


def test_sin_servicio_de_notificaciones_la_evaluacion_funciona_igual() -> None:
    e, repos, _ = entorno(con_notificaciones=False)

    aprobado, _ = e.evaluacion.aprobar("SIN-1", OPERADOR)

    assert aprobado.estado is EstadoSiniestro.APROBADO and bandeja(repos) == []


# --- Pago paramétrico ----------------------------------------------------------------------


def evento(evento_id: str = "EV-1") -> EventoParametrico:
    from datetime import UTC, datetime

    return EventoParametrico(
        evento_id=evento_id,
        tipo_evento="RETRASO_VUELO",
        valor_observado=Decimal("215"),
        fecha_evento=datetime(2026, 10, 21, 1, 0, tzinfo=UTC),
        numero_vuelo="AV123",
    )


def entorno_parametrico():
    e, repos, enviador = entorno()
    e.polizas.guardar(
        poliza(
            poliza_id="POL-PM",
            numero_poliza="SOL-PM-000001",
            ramo=RamoPoliza.PARAMETRICO,
            cobertura_principal=CoberturaPoliza(
                codigo="COMPENSACION_RETRASO_VUELO",
                nombre="Retraso de vuelo",
                suma_asegurada=Decimal("500000.00"),
                descripcion="tipo_evento=RETRASO_VUELO; numero_vuelo=AV123; umbral_disparo=180",
            ),
        )
    )
    telemetria = ServicioTelemetria(
        e.siniestros, e.polizas, reloj=lambda: AHORA, al_crear=e.evaluacion.aprobar_automatico
    )
    return e, repos, enviador, telemetria


def test_el_pago_automatico_de_un_seguro_parametrico_avisa_el_monto_y_la_poliza() -> None:
    e, repos, enviador, telemetria = entorno_parametrico()

    telemetria.procesar(evento())

    # Un solo aviso (el del pago), no además uno de cambio de estado.
    (n,) = [n for n in bandeja(repos) if n.datos.get("poliza_id") == "POL-PM"]
    assert n.tipo is TipoNotificacion.PAGO_PARAMETRICO
    assert n.cuerpo == "Se aprobó un pago de $500.000 COP por tu póliza SOL-PM-000001."
    assert n.datos["monto"] == "500000.00" and n.datos["numero_poliza"] == "SOL-PM-000001"
    (push,) = enviador.enviados
    assert push.cuerpo == n.cuerpo
    assert push.datos["siniestro_id"] == n.datos["siniestro_id"]  # abre el detalle


def test_el_mismo_evento_de_telemetria_no_avisa_dos_veces() -> None:
    e, repos, enviador, telemetria = entorno_parametrico()

    telemetria.procesar(evento("EV-1"))
    telemetria.procesar(evento("EV-1"))  # el proveedor reenvía el mismo evento

    pagos = [n for n in bandeja(repos) if n.tipo is TipoNotificacion.PAGO_PARAMETRICO]
    assert len(pagos) == 1 and len(enviador.enviados) == 1


def test_si_operaciones_aprueba_despues_un_parametrico_tambien_se_avisa_como_pago() -> None:
    e, repos, _ = entorno(
        siniestro(
            origen=OrigenSiniestro.AUTOMATICO, evento_id="EV-1", estimacion_danos=Decimal("700000")
        )
    )

    e.evaluacion.aprobar("SIN-1", OPERADOR)

    (n,) = bandeja(repos)
    assert n.tipo is TipoNotificacion.PAGO_PARAMETRICO
    assert "$700.000 COP" in n.cuerpo


def test_el_pago_parametrico_sin_dispositivos_queda_solo_en_la_bandeja() -> None:
    e, repos, enviador, telemetria = entorno_parametrico()
    repos.dispositivos.desactivar(CLIENTE, "token-1", AHORA)

    telemetria.procesar(evento())

    assert enviador.enviados == []
    assert any(n.tipo is TipoNotificacion.PAGO_PARAMETRICO for n in bandeja(repos))
