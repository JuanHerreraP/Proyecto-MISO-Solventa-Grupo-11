"""El siniestro paramétrico se aprueba solo y se desembolsa por la suma contratada (HU15)."""

from datetime import UTC, datetime
from decimal import Decimal

from app.desembolsos.modelos import EstadoDesembolso
from app.polizas.dominio.modelos import CoberturaPoliza, RamoPoliza
from app.siniestros.evaluacion import EVALUADOR_AUTOMATICO
from app.siniestros.modelos import EstadoSiniestro
from app.siniestros.telemetria import EventoParametrico, ServicioTelemetria
from tests.billetera.fabrica import poliza
from tests.desembolsos.fabrica import AHORA, crear_entorno


def evento(evento_id: str = "EV-1") -> EventoParametrico:
    return EventoParametrico(
        evento_id=evento_id,
        tipo_evento="RETRASO_VUELO",
        valor_observado=Decimal("215"),
        fecha_evento=datetime(2026, 10, 21, 1, 0, tzinfo=UTC),
        numero_vuelo="AV123",
    )


def entorno_parametrico():
    e = crear_entorno()
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
        e.siniestros,
        e.polizas,
        reloj=lambda: AHORA,
        al_crear=e.evaluacion.aprobar_automatico,
    )
    return e, telemetria


def test_el_evento_crea_aprueba_y_paga_el_siniestro() -> None:
    e, telemetria = entorno_parametrico()

    respuesta = telemetria.procesar(evento())

    creado = e.siniestros.obtener(respuesta.siniestro_id)
    assert creado.estado is EstadoSiniestro.APROBADO
    assert creado.evaluado_por == EVALUADOR_AUTOMATICO
    assert creado.monto_aprobado == Decimal("500000.00")
    desembolso = e.desembolsos.obtener_por_siniestro(creado.siniestro_id)
    assert desembolso.estado is EstadoDesembolso.COMPLETADA
    assert desembolso.monto == Decimal("500000.00")


def test_el_mismo_evento_no_paga_dos_veces() -> None:
    e, telemetria = entorno_parametrico()

    telemetria.procesar(evento())
    telemetria.procesar(evento())

    assert len(e.red.retiros) == 1


def test_si_el_desembolso_falla_operaciones_lo_reintenta(monkeypatch) -> None:
    e, telemetria = entorno_parametrico()
    desembolsar = e.desembolsos.desembolsar

    def fallar(_siniestro):
        raise RuntimeError("base caída")

    monkeypatch.setattr(e.desembolsos, "desembolsar", fallar)
    respuesta = telemetria.procesar(evento())

    # El evento se recibe igual; el siniestro queda aprobado y sin desembolso.
    assert respuesta.resultado.value == "SINIESTRO_CREADO"
    assert e.desembolsos.obtener_por_siniestro(respuesta.siniestro_id) is None

    monkeypatch.setattr(e.desembolsos, "desembolsar", desembolsar)
    desembolso = e.evaluacion.reintentar_desembolso(respuesta.siniestro_id)

    assert desembolso.estado is EstadoDesembolso.COMPLETADA
