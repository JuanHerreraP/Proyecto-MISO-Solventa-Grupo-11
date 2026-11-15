"""Comprobante de un pago aprobado: generación, idempotencia y consulta (HU21)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.cotizaciones import ActorCotizacion, TipoActorCotizacion, actor_actual
from app.api.pagos import obtener_comprobantes, obtener_servicio
from app.identidad.modelos import Rol
from app.main import app
from app.pagos.comprobantes import PagoSinComprobante, ServicioComprobantes, numero_de
from app.pagos.modelos import ConceptoComprobante, EstadoPago, MetodoPago
from app.pagos.modelos_db import ComprobanteDB
from app.pagos.pasarela_simulada import PasarelaSimulada
from app.pagos.repositorio_comprobantes import (
    RepositorioComprobantesEnMemoria,
    RepositorioComprobantesPostgres,
)
from app.pagos.servicio import ServicioPagos, en_cadena
from tests.primas_pendientes.fabrica import (
    CLIENTE,
    cotizacion_vigente,
    pago_aprobado,
)
from tests.renovaciones.fabrica import TITULAR, Entorno, crear_entorno, solicitud_pago

RUTA = "/api/v1/pagos"


def servicio_de(e: Entorno) -> ServicioComprobantes:
    return ServicioComprobantes(
        RepositorioComprobantesEnMemoria(),
        e.cotizaciones,
        e.renovaciones,
        e.polizas,
        reloj=e.reloj,
    )


def comprar(e: Entorno):
    """Paga una cotización nueva (una compra, no una renovación)."""
    e.cotizaciones.guardar(cotizacion_vigente())
    return e.pagar("COT-NUEVA")


def test_el_comprobante_de_una_compra_trae_lo_pagado_y_aun_no_tiene_poliza() -> None:
    e = crear_entorno()
    pago = comprar(e)

    comprobante = servicio_de(e).emitir(pago)

    assert comprobante.concepto is ConceptoComprobante.COMPRA
    assert comprobante.descripcion == "Prima de Microseguro de vida"
    assert comprobante.poliza_id is None and comprobante.numero_poliza is None
    assert comprobante.nombre_ramo == "Microseguro de vida"
    assert comprobante.monto == pago.monto and comprobante.moneda == "COP"
    assert comprobante.metodo is MetodoPago.TARJETA
    assert comprobante.referencia_pasarela == pago.referencia_pasarela
    assert comprobante.pagado_en == pago.actualizado_en
    assert comprobante.emitido_en == e.reloj.ahora
    assert comprobante.cliente_id == CLIENTE and comprobante.pago_id == pago.pago_id
    assert comprobante.numero == numero_de(pago)
    assert comprobante.numero.startswith("CP-20261210-")
    assert comprobante.numero.endswith(pago.pago_id[-8:].upper())


def test_el_comprobante_de_una_renovacion_trae_el_numero_de_la_poliza() -> None:
    e = crear_entorno()
    renovacion, _ = e.servicio.iniciar(TITULAR, "POL-VIDA-1", "k-1")
    pago = e.pagar(renovacion.cotizacion_id)

    comprobante = servicio_de(e).emitir(pago)

    assert comprobante.concepto is ConceptoComprobante.RENOVACION
    assert comprobante.poliza_id == "POL-VIDA-1"
    assert comprobante.numero_poliza == "SOL-2026-VIDA0001"
    assert comprobante.descripcion == (
        "Renovación de la póliza SOL-2026-VIDA0001 (Microseguro de vida)"
    )
    assert comprobante.monto == renovacion.prima_total


def test_emitir_dos_veces_devuelve_el_mismo_comprobante() -> None:
    e = crear_entorno()
    pago = comprar(e)
    servicio = servicio_de(e)

    primero = servicio.emitir(pago)
    e.reloj.avanzar(hours=1)
    segundo = servicio.emitir(pago)

    assert segundo == primero


def test_un_pago_que_no_esta_aprobado_no_tiene_comprobante() -> None:
    e = crear_entorno()
    e.cotizaciones.guardar(cotizacion_vigente())
    rechazado = e.pagar("COT-NUEVA", token="tok_rechazado_1")
    servicio = servicio_de(e)

    assert rechazado.estado is EstadoPago.RECHAZADO
    assert servicio.emitir(rechazado) is None
    with pytest.raises(PagoSinComprobante):
        servicio.obtener(rechazado)


def test_si_el_aviso_del_pago_fallo_el_comprobante_se_genera_al_consultarlo() -> None:
    e = crear_entorno()
    pago = comprar(e)
    servicio = servicio_de(e)

    comprobante = servicio.obtener(pago)

    assert comprobante.pago_id == pago.pago_id
    assert servicio.obtener(pago) == comprobante


def test_si_otra_solicitud_lo_creo_primero_se_devuelve_ese() -> None:
    e = crear_entorno()
    pago = comprar(e)
    original = servicio_de(e).emitir(pago)

    class RepositorioConCarrera(RepositorioComprobantesEnMemoria):
        def __init__(self):
            super().__init__()
            self.consultas = 0

        def por_pago(self, pago_id):
            self.consultas += 1
            return None if self.consultas == 1 else original

        def crear(self, comprobante):
            return False

    repo = RepositorioConCarrera()
    servicio = ServicioComprobantes(repo, e.cotizaciones, e.renovaciones, e.polizas)

    assert servicio.emitir(pago) == original


def test_un_pago_sin_cotizacion_igual_tiene_comprobante() -> None:
    e = crear_entorno()

    comprobante = servicio_de(e).emitir(pago_aprobado("COT-FANTASMA"))

    assert comprobante.nombre_ramo == "Seguro"
    assert comprobante.descripcion == "Prima de Seguro"


def test_el_pago_aprobado_genera_su_comprobante_con_el_aviso_encadenado() -> None:
    e = crear_entorno()
    comprobantes = servicio_de(e)
    pagos = ServicioPagos(
        e.pagos,
        e.cotizaciones,
        PasarelaSimulada(url_base="http://pruebas"),
        reloj=e.reloj,
        al_aprobar=en_cadena(e.servicio.aplicar_pago, comprobantes.emitir),
    )
    e.cotizaciones.guardar(cotizacion_vigente())

    pago, _ = pagos.pagar(CLIENTE, "llave-0001", solicitud_pago("COT-NUEVA"))

    assert comprobantes.obtener(pago).pago_id == pago.pago_id


def test_si_un_aviso_falla_los_demas_se_ejecutan() -> None:
    e = crear_entorno()
    comprobantes = servicio_de(e)

    def falla(pago):
        raise RuntimeError("no disponible")

    pago = comprar(e)

    en_cadena(falla, comprobantes.emitir)(pago)

    assert comprobantes.obtener(pago).pago_id == pago.pago_id


def test_el_repositorio_de_base_de_datos_guarda_y_lee_el_comprobante() -> None:
    e = crear_entorno()
    comprobante = servicio_de(e).emitir(comprar(e))
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    ComprobanteDB.__table__.create(engine)
    with sessionmaker(bind=engine)() as sesion:
        repo = RepositorioComprobantesPostgres(sesion)

        assert repo.crear(comprobante) is True
        sesion.expire_all()
        assert repo.por_pago(comprobante.pago_id) == comprobante
        assert repo.crear(comprobante) is False  # un pago, un comprobante
        assert repo.por_pago("PAG-otro") is None
    engine.dispose()


# --- API -----------------------------------------------------------------------------------


@pytest.fixture
def api():
    e = crear_entorno()
    comprobantes = servicio_de(e)
    app.dependency_overrides[obtener_servicio] = lambda: e.pagos_servicio
    app.dependency_overrides[obtener_comprobantes] = lambda: comprobantes
    app.dependency_overrides[actor_actual] = lambda: ActorCotizacion(
        tipo=TipoActorCotizacion.USUARIO, actor_id=CLIENTE, rol=Rol.CLIENTE
    )
    yield TestClient(app), e
    app.dependency_overrides.clear()


def test_el_cliente_consulta_el_comprobante_de_su_pago(api) -> None:
    cliente, e = api
    pago = comprar(e)

    respuesta = cliente.get(f"{RUTA}/{pago.pago_id}/comprobante")

    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert cuerpo["pago_id"] == pago.pago_id
    assert cuerpo["concepto"] == "COMPRA"
    assert cuerpo["descripcion"] == "Prima de Microseguro de vida"
    assert cuerpo["monto"] == "89000.00" and cuerpo["moneda"] == "COP"
    assert cuerpo["metodo"] == "TARJETA"
    assert cuerpo["numero"].startswith("CP-")
    assert "cliente_id" not in cuerpo


def test_un_pago_ajeno_responde_404(api) -> None:
    cliente, e = api
    pago = comprar(e)
    app.dependency_overrides[actor_actual] = lambda: ActorCotizacion(
        tipo=TipoActorCotizacion.USUARIO, actor_id="CLI-OTRO", rol=Rol.CLIENTE
    )

    assert cliente.get(f"{RUTA}/{pago.pago_id}/comprobante").status_code == 404
    assert cliente.get(f"{RUTA}/PAG-no-existe/comprobante").status_code == 404


def test_un_pago_rechazado_no_tiene_comprobante(api) -> None:
    cliente, e = api
    e.cotizaciones.guardar(cotizacion_vigente())
    rechazado = e.pagar("COT-NUEVA", token="tok_rechazado_1")

    respuesta = cliente.get(f"{RUTA}/{rechazado.pago_id}/comprobante")

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "PAGO_SIN_COMPROBANTE"


def test_solo_el_cliente_consulta_comprobantes(api) -> None:
    cliente, e = api
    pago = comprar(e)
    app.dependency_overrides[actor_actual] = lambda: ActorCotizacion(
        tipo=TipoActorCotizacion.USUARIO, actor_id="ASE-1", rol=Rol.ASESOR_VENTAS
    )

    assert cliente.get(f"{RUTA}/{pago.pago_id}/comprobante").status_code == 403


def test_el_cableado_real_genera_el_comprobante_al_aprobarse_el_pago() -> None:
    from app.api.pagos import armar_comprobantes
    from app.cotizaciones.repositorio import RepositorioCotizacionesPostgres
    from app.infraestructura.database import Base
    from app.perfilamiento.enriquecimiento.memoria import RepositorioConsentimientosEnMemoria
    from app.perfilamiento.repositorio import RepositorioPerfilesEnMemoria

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as sesion:
        RepositorioCotizacionesPostgres(sesion).guardar(
            cotizacion_vigente().model_copy(
                update={
                    "creada_en": datetime.now(UTC) - timedelta(hours=1),
                    "vigente_hasta": datetime.now(UTC) + timedelta(days=5),
                }
            )
        )
        servicio = obtener_servicio(
            db=sesion,
            pasarela=PasarelaSimulada(url_base="http://pruebas"),
            perfiles=RepositorioPerfilesEnMemoria(),
            consentimientos=RepositorioConsentimientosEnMemoria(),
        )

        pago, _ = servicio.pagar(CLIENTE, "llave-0001", solicitud_pago("COT-NUEVA"))

        assert pago.estado is EstadoPago.APROBADO
        guardado = RepositorioComprobantesPostgres(sesion).por_pago(pago.pago_id)
        assert guardado is not None and guardado.descripcion == "Prima de Microseguro de vida"
        assert armar_comprobantes(sesion).obtener(pago) == guardado
    engine.dispose()


# --- Concepto del pago (compra o renovación) -----------------------------------------------


def test_el_concepto_distingue_una_compra_de_una_renovacion() -> None:
    e = crear_entorno()
    comprobantes = servicio_de(e)
    renovacion, _ = e.servicio.iniciar(TITULAR, "POL-VIDA-1", "k-1")

    assert comprobantes.concepto_de(renovacion.cotizacion_id) is ConceptoComprobante.RENOVACION
    assert comprobantes.concepto_de("COT-NUEVA") is ConceptoComprobante.COMPRA


def test_sin_saber_de_renovaciones_el_pago_se_considera_una_compra() -> None:
    e = crear_entorno()
    pago = comprar(e)

    assert e.pagos_servicio.con_concepto(pago).concepto is ConceptoComprobante.COMPRA


def test_la_api_de_pagos_informa_el_concepto_de_cada_pago(api) -> None:
    cliente, e = api
    comprobantes = servicio_de(e)
    app.dependency_overrides[obtener_servicio] = lambda: ServicioPagos(
        e.pagos,
        e.cotizaciones,
        PasarelaSimulada(url_base="http://pruebas"),
        reloj=e.reloj,
        concepto_de=comprobantes.concepto_de,
    )
    compra = comprar(e)
    renovacion, _ = e.servicio.iniciar(TITULAR, "POL-VIDA-1", "k-1")
    renovada = e.pagar(renovacion.cotizacion_id, llave="llave-0002")

    lista = {p["pago_id"]: p for p in cliente.get(RUTA).json()}
    uno = cliente.get(f"{RUTA}/{renovada.pago_id}").json()
    nuevo = cliente.post(
        RUTA,
        json={"cotizacion_id": "COT-VIDA-1", "metodo": "TARJETA", "token_tarjeta": "tok_visa_ok"},
        headers={"Idempotency-Key": "llave-0003"},
    )

    assert lista[compra.pago_id]["concepto"] == "COMPRA"
    assert lista[renovada.pago_id]["concepto"] == "RENOVACION"
    assert uno["concepto"] == "RENOVACION"
    assert "huella_solicitud" not in uno
    assert nuevo.status_code in (201, 409) and (
        nuevo.status_code == 409 or nuevo.json()["concepto"] == "COMPRA"
    )
