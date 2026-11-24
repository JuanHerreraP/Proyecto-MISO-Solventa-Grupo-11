"""Pago paramétrico por eventos: publicación, consumidor idempotente, barrido y worker."""

import json
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.desembolsos import construir_evaluacion
from app.desembolsos import worker as worker_pagos
from app.desembolsos.barrido import barrer_pendientes
from app.desembolsos.consumidor import (
    ConsumidorPagos,
    DesembolsoPendiente,
    ResultadoConsumo,
    SiniestroDelEventoNoEncontrado,
)
from app.desembolsos.modelos import EstadoDesembolso
from app.desembolsos.modelos_db import CuentaDesembolsoDB, DesembolsoDB
from app.desembolsos.pendientes import (
    RepositorioPendientesPagoEnMemoria,
    RepositorioPendientesPagoPostgres,
)
from app.desembolsos.puertos import RedNoDisponible
from app.desembolsos.red_simulada import RedDesembolsosSimulada
from app.desembolsos.repositorio import RepositorioCuentasPostgres, RepositorioDesembolsosPostgres
from app.desembolsos.servicio import ServicioDesembolsos
from app.eventos.modelos import EventoNegocio
from app.eventos.procesados import (
    EventoProcesadoDB,
    RepositorioEventosProcesadosEnMemoria,
)
from app.eventos.publicador import PublicadorEnMemoria, PublicadorSNS, publicador_negocio
from app.polizas.modelos_db import PolizaDB
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.siniestros.evaluacion import ServicioEvaluacion
from app.siniestros.eventos import evento_pago_parametrico
from app.siniestros.modelos import EstadoSiniestro, OrigenSiniestro
from app.siniestros.modelos_db import SiniestroDB
from app.siniestros.repositorio import RepositorioSiniestrosPostgres
from tests.billetera.fabrica import poliza
from tests.desembolsos.fabrica import AHORA, CLIENTE, OPERADOR, crear_entorno, cuenta, siniestro

DIEZ_MINUTOS = timedelta(minutes=10)


def aprobado_automatico(**cambios):
    """Un siniestro paramétrico aprobado hace diez minutos, que aún no tiene desembolso."""
    datos = {
        "origen": OrigenSiniestro.AUTOMATICO,
        "estado": EstadoSiniestro.APROBADO,
        "monto_aprobado": Decimal("500000.00"),
        "evaluado_por": "SISTEMA",
        "evaluado_en": AHORA - DIEZ_MINUTOS,
    }
    datos.update(cambios)
    return siniestro(**datos)


class _PublicadorQueFalla:
    def __init__(self, fallos: int = 1):
        self.fallos = fallos
        self.eventos: list[EventoNegocio] = []

    def publicar(self, evento):
        if self.fallos > 0:
            self.fallos -= 1
            raise RuntimeError("SNS no responde")
        self.eventos.append(evento)
        return f"ok-{len(self.eventos)}"


def evaluacion_con(entorno, publicador):
    return ServicioEvaluacion(
        entorno.siniestros,
        entorno.polizas,
        entorno.desembolsos,
        reloj=lambda: AHORA,
        publicador=publicador,
    )


# --- Siniestros publica el evento -----------------------------------------------------------


def test_con_publicador_la_aprobacion_automatica_publica_y_no_ordena_el_pago() -> None:
    entorno = crear_entorno(siniestro(origen=OrigenSiniestro.AUTOMATICO))
    publicador = PublicadorEnMemoria()

    resultado = evaluacion_con(entorno, publicador).aprobar_automatico(
        entorno.siniestros.obtener("SIN-1")
    )

    assert resultado is None
    aprobado = entorno.siniestros.obtener("SIN-1")
    assert aprobado.estado is EstadoSiniestro.APROBADO
    assert aprobado.evaluado_por == "SISTEMA"
    assert entorno.repo_desembolsos.obtener_por_siniestro("SIN-1") is None
    assert entorno.red.retiros == [] and entorno.red.transferencias == []
    [evento] = publicador.eventos
    assert evento.evento_id == "PAGO_PARAMETRICO:SIN-1"
    assert evento.datos["siniestro_id"] == "SIN-1"
    assert evento.datos["cliente_id"] == CLIENTE
    assert evento.datos["monto_aprobado"] == "850000.00"


def test_sin_publicador_la_aprobacion_automatica_ordena_el_pago_como_antes() -> None:
    entorno = crear_entorno(siniestro(origen=OrigenSiniestro.AUTOMATICO))

    desembolso = entorno.evaluacion.aprobar_automatico(entorno.siniestros.obtener("SIN-1"))

    assert desembolso is not None
    assert desembolso.estado is EstadoDesembolso.COMPLETADA
    assert len(entorno.red.retiros) == 1


def test_si_sns_falla_el_siniestro_queda_aprobado_y_sin_pago_para_el_barrido() -> None:
    entorno = crear_entorno(siniestro(origen=OrigenSiniestro.AUTOMATICO))
    publicador = _PublicadorQueFalla(fallos=1)

    resultado = evaluacion_con(entorno, publicador).aprobar_automatico(
        entorno.siniestros.obtener("SIN-1")
    )

    assert resultado is None
    assert entorno.siniestros.obtener("SIN-1").estado is EstadoSiniestro.APROBADO
    assert entorno.repo_desembolsos.obtener_por_siniestro("SIN-1") is None
    assert publicador.eventos == []


def test_aprobar_el_mismo_siniestro_dos_veces_publica_el_mismo_evento() -> None:
    entorno = crear_entorno(siniestro(origen=OrigenSiniestro.AUTOMATICO))
    publicador = PublicadorEnMemoria()
    evaluacion = evaluacion_con(entorno, publicador)

    evaluacion.aprobar_automatico(entorno.siniestros.obtener("SIN-1"))
    evaluacion.aprobar_automatico(entorno.siniestros.obtener("SIN-1"))

    assert [e.evento_id for e in publicador.eventos] == ["PAGO_PARAMETRICO:SIN-1"] * 2


def test_la_aprobacion_manual_de_operaciones_sigue_pagando_en_linea() -> None:
    entorno = crear_entorno(siniestro())
    publicador = PublicadorEnMemoria()

    aprobado, desembolso = evaluacion_con(entorno, publicador).aprobar("SIN-1", OPERADOR)

    assert aprobado.estado is EstadoSiniestro.APROBADO
    assert desembolso.estado is EstadoDesembolso.COMPLETADA
    assert publicador.eventos == []


def test_un_siniestro_que_no_existe_no_publica_nada() -> None:
    entorno = crear_entorno()
    publicador = PublicadorEnMemoria()
    fantasma = siniestro(siniestro_id="SIN-NO-EXISTE", origen=OrigenSiniestro.AUTOMATICO)

    assert evaluacion_con(entorno, publicador).aprobar_automatico(fantasma) is None
    assert publicador.eventos == []


# --- Consumidor de pagos --------------------------------------------------------------------


def consumidor(entorno, procesados=None):
    return ConsumidorPagos(
        entorno.desembolsos,
        entorno.siniestros,
        procesados or RepositorioEventosProcesadosEnMemoria(),
        reloj=lambda: AHORA,
    )


def test_el_consumidor_ordena_el_desembolso_y_marca_el_evento() -> None:
    entorno = crear_entorno(aprobado_automatico())
    procesados = RepositorioEventosProcesadosEnMemoria()
    evento = evento_pago_parametrico(entorno.siniestros.obtener("SIN-1"))

    resultado = consumidor(entorno, procesados).procesar(evento)

    assert resultado is ResultadoConsumo.PAGADO
    desembolso = entorno.repo_desembolsos.obtener_por_siniestro("SIN-1")
    assert desembolso.estado is EstadoDesembolso.COMPLETADA
    assert desembolso.monto == Decimal("500000.00")
    assert procesados.ya_procesado(evento.evento_id, "pagos")


def test_el_mismo_evento_dos_veces_paga_una_sola_vez() -> None:
    entorno = crear_entorno(aprobado_automatico())
    procesados = RepositorioEventosProcesadosEnMemoria()
    evento = evento_pago_parametrico(entorno.siniestros.obtener("SIN-1"))
    consumidor_pagos = consumidor(entorno, procesados)

    primero = consumidor_pagos.procesar(evento)
    segundo = consumidor_pagos.procesar(evento)

    assert (primero, segundo) == (ResultadoConsumo.PAGADO, ResultadoConsumo.DUPLICADO)
    assert len(entorno.red.retiros) == 1


def test_aunque_llegue_con_otro_identificador_el_siniestro_no_se_paga_dos_veces() -> None:
    # La restricción única del desembolso protege aun si el evento repetido no se reconoce.
    entorno = crear_entorno(aprobado_automatico())
    original = evento_pago_parametrico(entorno.siniestros.obtener("SIN-1"))
    repetido = original.model_copy(update={"evento_id": "OTRO-ID"})
    consumidor_pagos = consumidor(entorno)

    assert consumidor_pagos.procesar(original) is ResultadoConsumo.PAGADO
    assert consumidor_pagos.procesar(repetido) is ResultadoConsumo.PAGADO

    assert len(entorno.red.retiros) == 1


def test_si_la_red_cae_el_evento_no_se_marca_y_el_reintento_completa_el_pago() -> None:
    entorno = crear_entorno(aprobado_automatico())
    procesados = RepositorioEventosProcesadosEnMemoria()
    evento = evento_pago_parametrico(entorno.siniestros.obtener("SIN-1"))
    consumidor_pagos = consumidor(entorno, procesados)
    entorno.red.caida = True

    with pytest.raises(DesembolsoPendiente):
        consumidor_pagos.procesar(evento)

    assert not procesados.ya_procesado(evento.evento_id, "pagos")
    pendiente = entorno.repo_desembolsos.obtener_por_siniestro("SIN-1")
    assert pendiente.estado is EstadoDesembolso.PENDIENTE

    entorno.red.caida = False
    assert consumidor_pagos.procesar(evento) is ResultadoConsumo.PAGADO
    assert entorno.repo_desembolsos.obtener_por_siniestro("SIN-1").estado is (
        EstadoDesembolso.COMPLETADA
    )
    assert procesados.ya_procesado(evento.evento_id, "pagos")
    assert len(entorno.red.retiros) == 1


def test_un_pago_fallido_por_la_cuenta_se_da_por_procesado_para_no_ciclar() -> None:
    entorno = crear_entorno(aprobado_automatico())
    entorno.desembolsos.registrar_cuenta(CLIENTE, cuenta("12340000"))  # termina en 0000: falla
    procesados = RepositorioEventosProcesadosEnMemoria()
    evento = evento_pago_parametrico(entorno.siniestros.obtener("SIN-1"))

    resultado = consumidor(entorno, procesados).procesar(evento)

    assert resultado is ResultadoConsumo.PAGADO
    assert entorno.repo_desembolsos.obtener_por_siniestro("SIN-1").estado is (
        EstadoDesembolso.FALLIDA
    )
    assert procesados.ya_procesado(evento.evento_id, "pagos")


def test_un_evento_de_un_siniestro_inexistente_falla_para_que_acabe_en_la_dlq() -> None:
    entorno = crear_entorno()
    evento = evento_pago_parametrico(aprobado_automatico(siniestro_id="SIN-FANTASMA"))

    with pytest.raises(SiniestroDelEventoNoEncontrado):
        consumidor(entorno).procesar(evento)


# --- Barrido de pendientes ------------------------------------------------------------------


def pendientes_de(entorno):
    return RepositorioPendientesPagoEnMemoria(entorno.siniestros, entorno.repo_desembolsos)


def test_el_barrido_republica_lo_aprobado_que_quedo_sin_pago() -> None:
    entorno = crear_entorno(
        aprobado_automatico(siniestro_id="SIN-VIEJO"),
        aprobado_automatico(siniestro_id="SIN-RECIENTE", evaluado_en=AHORA - timedelta(minutes=1)),
        aprobado_automatico(siniestro_id="SIN-PAGADO"),
        aprobado_automatico(siniestro_id="SIN-MANUAL", origen=OrigenSiniestro.MANUAL),
    )
    entorno.desembolsos.desembolsar(entorno.siniestros.obtener("SIN-PAGADO"))
    publicador = PublicadorEnMemoria()

    cantidad = barrer_pendientes(
        pendientes_de(entorno),
        entorno.siniestros,
        publicador,
        antes_de=AHORA - timedelta(minutes=5),
    )

    assert cantidad == 1
    assert [e.evento_id for e in publicador.eventos] == ["PAGO_PARAMETRICO:SIN-VIEJO"]


def test_el_barrido_tambien_retoma_un_desembolso_que_sigue_pendiente() -> None:
    entorno = crear_entorno(aprobado_automatico())
    entorno.red.caida = True
    entorno.desembolsos.desembolsar(entorno.siniestros.obtener("SIN-1"))
    publicador = PublicadorEnMemoria()

    reciente = barrer_pendientes(
        pendientes_de(entorno), entorno.siniestros, publicador, antes_de=AHORA - DIEZ_MINUTOS
    )
    viejo = barrer_pendientes(
        pendientes_de(entorno), entorno.siniestros, publicador, antes_de=AHORA + DIEZ_MINUTOS
    )

    assert (reciente, viejo) == (0, 1)


def test_un_fallo_al_republicar_no_detiene_el_barrido() -> None:
    entorno = crear_entorno(
        aprobado_automatico(siniestro_id="SIN-1"), aprobado_automatico(siniestro_id="SIN-2")
    )
    publicador = _PublicadorQueFalla(fallos=1)

    cantidad = barrer_pendientes(
        pendientes_de(entorno), entorno.siniestros, publicador, antes_de=AHORA
    )

    assert cantidad == 1
    assert len(publicador.eventos) == 1


def test_el_barrido_respeta_el_limite() -> None:
    entorno = crear_entorno(*(aprobado_automatico(siniestro_id=f"SIN-{n}") for n in range(5)))
    publicador = PublicadorEnMemoria()

    cantidad = barrer_pendientes(
        pendientes_de(entorno), entorno.siniestros, publicador, antes_de=AHORA, limite=2
    )

    assert cantidad == 2


# --- Sobre la base de datos (SQLite en memoria) ----------------------------------------------


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for tabla in (PolizaDB, SiniestroDB, DesembolsoDB, CuentaDesembolsoDB, EventoProcesadoDB):
        tabla.__table__.create(engine)
    with sessionmaker(bind=engine)() as sesion:
        RepositorioPolizasPostgres(sesion).guardar(poliza())
        yield sesion
    engine.dispose()


def guardar(db, *siniestros):
    repo = RepositorioSiniestrosPostgres(db)
    for s in siniestros:
        repo.guardar(s)


def evento_de(siniestro_id: str) -> str:
    return evento_pago_parametrico(aprobado_automatico(siniestro_id=siniestro_id)).como_json()


def test_el_origen_de_pendientes_distingue_los_casos_en_la_base(db) -> None:
    guardar(
        db,
        aprobado_automatico(siniestro_id="SIN-SIN-PAGO"),
        aprobado_automatico(siniestro_id="SIN-PAGADO"),
        aprobado_automatico(siniestro_id="SIN-PENDIENTE"),
        aprobado_automatico(siniestro_id="SIN-RECIENTE", evaluado_en=AHORA),
        aprobado_automatico(siniestro_id="SIN-MANUAL", origen=OrigenSiniestro.MANUAL),
        siniestro(siniestro_id="SIN-REGISTRADO", origen=OrigenSiniestro.AUTOMATICO),
    )
    servicio = ServicioDesembolsos(
        RepositorioDesembolsosPostgres(db),
        RepositorioCuentasPostgres(db),
        RedDesembolsosSimulada(),
        reloj=lambda: AHORA - DIEZ_MINUTOS,
    )
    servicio.desembolsar(RepositorioSiniestrosPostgres(db).obtener("SIN-PAGADO"))

    class RedCaida(RedDesembolsosSimulada):
        def emitir_codigo_retiro(self, orden):
            raise RedNoDisponible("caída")

    ServicioDesembolsos(
        RepositorioDesembolsosPostgres(db),
        RepositorioCuentasPostgres(db),
        RedCaida(),
        reloj=lambda: AHORA - DIEZ_MINUTOS,
    ).desembolsar(RepositorioSiniestrosPostgres(db).obtener("SIN-PENDIENTE"))

    ids = RepositorioPendientesPagoPostgres(db).ids_pendientes(AHORA - timedelta(minutes=5), 100)

    assert sorted(ids) == ["SIN-PENDIENTE", "SIN-SIN-PAGO"]
    # El límite se respeta: primero van los aprobados que nunca llegaron a pagarse.
    assert RepositorioPendientesPagoPostgres(db).ids_pendientes(AHORA, 1) == ["SIN-SIN-PAGO"]


def test_procesar_mensaje_paga_una_sola_vez_aunque_el_mensaje_llegue_dos_veces(
    db, monkeypatch
) -> None:
    guardar(db, aprobado_automatico())
    monkeypatch.setattr(worker_pagos, "SessionLocal", lambda: db)
    cuerpo = evento_de("SIN-1")

    primero = worker_pagos.procesar_mensaje(cuerpo)
    segundo = worker_pagos.procesar_mensaje(cuerpo)

    assert (primero, segundo) == (ResultadoConsumo.PAGADO, ResultadoConsumo.DUPLICADO)
    desembolso = RepositorioDesembolsosPostgres(db).obtener_por_siniestro("SIN-1")
    assert desembolso.estado is EstadoDesembolso.COMPLETADA
    assert db.query(DesembolsoDB).count() == 1


def test_procesar_mensaje_lee_tambien_el_sobre_de_sns(db, monkeypatch) -> None:
    guardar(db, aprobado_automatico())
    monkeypatch.setattr(worker_pagos, "SessionLocal", lambda: db)
    sobre = json.dumps({"Type": "Notification", "Message": evento_de("SIN-1")})

    assert worker_pagos.procesar_mensaje(sobre) is ResultadoConsumo.PAGADO


def test_el_barrido_del_worker_republica_lo_pendiente(db, monkeypatch) -> None:
    guardar(db, aprobado_automatico())
    monkeypatch.setattr(worker_pagos, "SessionLocal", lambda: db)
    monkeypatch.setenv("PAGOS_BARRIDO_ANTIGUEDAD", "300")
    publicador = PublicadorEnMemoria()

    cantidad = worker_pagos.barrer(publicador, ahora=AHORA)

    assert cantidad == 1
    assert publicador.eventos[0].evento_id == "PAGO_PARAMETRICO:SIN-1"


# --- Bucle del worker -----------------------------------------------------------------------


class _Sqs:
    def __init__(self, mensajes):
        self.mensajes = mensajes
        self.borrados: list[str] = []
        self.pedidos = 0

    def receive_message(self, **_):
        self.pedidos += 1
        return {"Messages": self.mensajes} if self.pedidos == 1 else {}

    def delete_message(self, QueueUrl, ReceiptHandle):  # noqa: N803 — firma de boto3.
        self.borrados.append(ReceiptHandle)


def test_solo_se_borra_el_mensaje_que_se_proceso_bien(monkeypatch) -> None:
    from concurrent.futures import ThreadPoolExecutor

    def procesar(cuerpo):
        if cuerpo == "malo":
            raise RuntimeError("falla")
        return ResultadoConsumo.PAGADO

    monkeypatch.setattr(worker_pagos, "procesar_mensaje", procesar)
    sqs = _Sqs(
        [
            {"Body": "bueno", "ReceiptHandle": "r-bueno"},
            {"Body": "malo", "ReceiptHandle": "r-malo"},
        ]
    )

    with ThreadPoolExecutor(max_workers=1) as ejecutor:
        worker_pagos._consumir_lote(sqs, "https://sqs/pagos", ejecutor)

    assert sqs.borrados == ["r-bueno"]


def test_si_no_hay_mensajes_el_lote_no_hace_nada(monkeypatch) -> None:
    from concurrent.futures import ThreadPoolExecutor

    sqs = _Sqs([])
    sqs.pedidos = 1  # la primera llamada ya devolvió mensajes: ahora responde vacío.

    with ThreadPoolExecutor(max_workers=1) as ejecutor:
        worker_pagos._consumir_lote(sqs, "https://sqs/pagos", ejecutor)

    assert sqs.borrados == []


def test_el_worker_exige_la_cola(monkeypatch) -> None:
    monkeypatch.delenv("SQS_PAGOS_QUEUE_URL", raising=False)

    with pytest.raises(ValueError, match="SQS_PAGOS_QUEUE_URL"):
        worker_pagos.ejecutar()


def test_el_bucle_consume_y_hace_el_barrido_cuando_toca(monkeypatch) -> None:
    import boto3

    monkeypatch.setenv("SQS_PAGOS_QUEUE_URL", "https://sqs/pagos")
    monkeypatch.setenv("PAGOS_BARRIDO_SEGUNDOS", "1")
    monkeypatch.setattr(worker_pagos, "_preparar_esquema", lambda: None)
    sqs = _Sqs([{"Body": "ok", "ReceiptHandle": "r-1"}])
    monkeypatch.setattr(boto3, "client", lambda *_, **__: sqs)
    monkeypatch.setattr(worker_pagos, "procesar_mensaje", lambda _c: ResultadoConsumo.PAGADO)
    publicador = PublicadorEnMemoria()
    monkeypatch.setattr(worker_pagos, "publicador_negocio", lambda: publicador)
    reloj = iter([0, 100, 100, 200, 200, 300, 300])
    monkeypatch.setattr(worker_pagos, "time", SimpleNamespace(monotonic=lambda: next(reloj)))
    barridos = []
    monkeypatch.setattr(worker_pagos, "barrer", lambda p: barridos.append(p) or 0)
    vueltas = iter([False, True])

    worker_pagos.ejecutar(parar=lambda: next(vueltas))

    assert sqs.borrados == ["r-1"]
    assert barridos == [publicador]


def test_el_bucle_sin_topico_no_hace_barrido(monkeypatch) -> None:
    import boto3

    monkeypatch.setenv("SQS_PAGOS_QUEUE_URL", "https://sqs/pagos")
    monkeypatch.setattr(worker_pagos, "_preparar_esquema", lambda: None)
    monkeypatch.setattr(boto3, "client", lambda *_, **__: _Sqs([]))
    monkeypatch.setattr(worker_pagos, "publicador_negocio", lambda: None)
    monkeypatch.setattr(
        worker_pagos, "barrer", lambda _p: pytest.fail("No debe barrer sin un tópico.")
    )
    vueltas = iter([False, True])

    worker_pagos.ejecutar(parar=lambda: next(vueltas))


def test_un_fallo_en_el_ciclo_no_mata_al_worker(monkeypatch) -> None:
    import boto3

    monkeypatch.setenv("SQS_PAGOS_QUEUE_URL", "https://sqs/pagos")
    monkeypatch.setenv("PAGOS_BARRIDO_SEGUNDOS", "1")
    monkeypatch.setattr(worker_pagos, "_preparar_esquema", lambda: None)
    monkeypatch.setattr(boto3, "client", lambda *_, **__: _Sqs([]))
    monkeypatch.setattr(worker_pagos, "publicador_negocio", lambda: PublicadorEnMemoria())
    monkeypatch.setattr(
        worker_pagos,
        "_consumir_lote",
        lambda *_: (_ for _ in ()).throw(RuntimeError("SQS caído")),
    )
    reloj = iter([0, 100, 100, 200, 200])
    monkeypatch.setattr(worker_pagos, "time", SimpleNamespace(monotonic=lambda: next(reloj)))
    monkeypatch.setattr(
        worker_pagos, "barrer", lambda _p: (_ for _ in ()).throw(RuntimeError("BD caída"))
    )
    vueltas = iter([False, True])

    worker_pagos.ejecutar(parar=lambda: next(vueltas))  # no lanza: el worker sigue vivo.


def test_la_concurrencia_se_lee_del_entorno_con_valores_seguros(monkeypatch) -> None:
    monkeypatch.setenv("PAGOS_WORKER_CONCURRENCIA", "7")
    assert worker_pagos.concurrencia() == 7
    monkeypatch.setenv("PAGOS_WORKER_CONCURRENCIA", "abc")
    assert worker_pagos.concurrencia() == 4
    monkeypatch.setenv("PAGOS_WORKER_CONCURRENCIA", "0")
    assert worker_pagos.concurrencia() == 1


# --- Armado del servicio --------------------------------------------------------------------


def test_construir_evaluacion_usa_el_publicador_solo_si_hay_topico(db, monkeypatch) -> None:
    publicador_negocio.cache_clear()
    monkeypatch.delenv("SNS_TOPIC_ARN", raising=False)
    assert construir_evaluacion(db)._publicador is None

    publicador_negocio.cache_clear()
    monkeypatch.setenv("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:1:eventos")
    assert isinstance(construir_evaluacion(db)._publicador, PublicadorSNS)
    publicador_negocio.cache_clear()
