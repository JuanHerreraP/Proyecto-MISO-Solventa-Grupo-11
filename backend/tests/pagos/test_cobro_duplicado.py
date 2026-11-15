"""Una cotización solo puede tener un pago aprobado, también bajo concurrencia (HU21)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cotizaciones.dominio.modelos import EstadoCotizacion
from app.infraestructura import database
from app.pagos.modelos import EstadoPago, MetodoPago, Pago
from app.pagos.modelos_db import PagoDB
from app.pagos.puertos import PagoAprobadoDuplicado
from app.pagos.repositorio import RepositorioPagosEnMemoria, RepositorioPagosPostgres
from app.pagos.servicio import MOTIVO_COBRO_DUPLICADO
from tests.pagos.test_pagos import confirmar, entorno, pagar  # noqa: F401

AHORA = datetime(2027, 1, 1, tzinfo=UTC)


def pago(pago_id: str, estado: EstadoPago, cotizacion_id: str = "COT-001") -> Pago:
    return Pago(
        pago_id=pago_id,
        cotizacion_id=cotizacion_id,
        cliente_id="CLI-001",
        idempotency_key=f"llave-{pago_id}",
        huella_solicitud="a" * 64,
        metodo=MetodoPago.TARJETA,
        monto=Decimal("45000.00"),
        moneda="COP",
        estado=estado,
        referencia_pasarela=f"PSP-{pago_id}",
        creado_en=AHORA,
        actualizado_en=AHORA,
    )


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    PagoDB.__table__.create(engine)
    with sessionmaker(bind=engine)() as sesion:
        yield sesion
    engine.dispose()


@pytest.mark.parametrize("repositorio", [RepositorioPagosEnMemoria, "postgres"])
def test_no_se_guardan_dos_pagos_aprobados_de_la_misma_cotizacion(repositorio, db) -> None:
    repo = RepositorioPagosPostgres(db) if repositorio == "postgres" else repositorio()
    repo.guardar(pago("PAG-1", EstadoPago.APROBADO))

    with pytest.raises(PagoAprobadoDuplicado) as error:
        repo.guardar(pago("PAG-2", EstadoPago.APROBADO))

    assert error.value.pago_id == "PAG-1"
    assert repo.obtener_aprobado_de_cotizacion("COT-001").pago_id == "PAG-1"
    assert repo.obtener("PAG-2") is None


@pytest.mark.parametrize("repositorio", [RepositorioPagosEnMemoria, "postgres"])
def test_lo_que_no_es_un_segundo_aprobado_se_guarda_sin_problema(repositorio, db) -> None:
    repo = RepositorioPagosPostgres(db) if repositorio == "postgres" else repositorio()
    repo.guardar(pago("PAG-1", EstadoPago.APROBADO))

    repo.guardar(pago("PAG-2", EstadoPago.PENDIENTE))
    repo.guardar(pago("PAG-3", EstadoPago.RECHAZADO))
    repo.guardar(pago("PAG-4", EstadoPago.APROBADO, cotizacion_id="COT-OTRA"))
    repo.guardar(pago("PAG-1", EstadoPago.APROBADO))  # volver a guardar el mismo no choca

    assert len(repo.listar_por_cotizacion("COT-001")) == 3
    assert repo.obtener_aprobado_de_cotizacion("COT-OTRA").pago_id == "PAG-4"


def test_la_sesion_sigue_usable_tras_el_choque(db) -> None:
    repo = RepositorioPagosPostgres(db)
    repo.guardar(pago("PAG-1", EstadoPago.APROBADO))
    with pytest.raises(PagoAprobadoDuplicado):
        repo.guardar(pago("PAG-2", EstadoPago.APROBADO))

    repo.guardar(pago("PAG-3", EstadoPago.RECHAZADO))

    assert repo.obtener("PAG-3").estado is EstadoPago.RECHAZADO


def test_un_error_de_integridad_distinto_se_propaga(db) -> None:
    from sqlalchemy.exc import IntegrityError

    repo = RepositorioPagosPostgres(db)
    repo.guardar(pago("PAG-1", EstadoPago.PENDIENTE))
    repetida = pago("PAG-2", EstadoPago.PENDIENTE).model_copy(
        update={"referencia_pasarela": "PSP-PAG-1"}  # la referencia de la pasarela es única
    )

    with pytest.raises(IntegrityError):
        repo.guardar(repetida)


def test_el_cobro_que_llega_tarde_queda_rechazado_como_duplicado(entorno) -> None:  # noqa: F811
    cliente, cotizaciones, _ = entorno
    # El cliente abre un pago PSE y, sin esperar, paga con tarjeta: la tarjeta se aprueba.
    pse = pagar(
        cliente,
        {"cotizacion_id": "COT-001", "metodo": "PSE", "codigo_banco": "1007"},
        llave="llave-pse-1",
    ).json()
    tarjeta = pagar(
        cliente,
        {"cotizacion_id": "COT-001", "metodo": "TARJETA", "token_tarjeta": "tok_visa_aprobado"},
        llave="llave-tarjeta-1",
    ).json()
    assert tarjeta["estado"] == "APROBADO"

    # Luego el banco confirma el PSE: se cobraría dos veces la misma cotización.
    respuesta = confirmar(cliente, pse["referencia_pasarela"], "APROBADO")

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "RECHAZADO"
    pagos = {p["pago_id"]: p for p in cliente.get("/api/v1/pagos").json()}
    assert pagos[pse["pago_id"]]["estado"] == "RECHAZADO"
    assert pagos[pse["pago_id"]]["motivo_rechazo"] == MOTIVO_COBRO_DUPLICADO
    assert [p["estado"] for p in pagos.values()].count("APROBADO") == 1
    assert cotizaciones.obtener("COT-001").estado is EstadoCotizacion.ACEPTADA


def test_el_indice_se_crea_en_una_base_que_ya_tenia_pagos(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    PagoDB.__table__.create(engine)
    with engine.begin() as conexion:
        conexion.execute(text("DROP INDEX uq_pagos_cotizacion_aprobado"))
    monkeypatch.setattr(database, "engine", engine)
    assert "uq_pagos_cotizacion_aprobado" not in {
        i["name"] for i in inspect(engine).get_indexes("pagos")
    }

    database._crear_indice_pago_aprobado(inspect(engine))

    assert "uq_pagos_cotizacion_aprobado" in {
        i["name"] for i in inspect(engine).get_indexes("pagos")
    }
    database._crear_indice_pago_aprobado(inspect(engine))  # repetirlo no falla
    engine.dispose()


def test_si_ya_hay_duplicados_el_arranque_no_falla(monkeypatch, caplog) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    PagoDB.__table__.create(engine)
    with engine.begin() as conexion:
        conexion.execute(text("DROP INDEX uq_pagos_cotizacion_aprobado"))
    with sessionmaker(bind=engine)() as sesion:
        repo = RepositorioPagosPostgres(sesion)
        repo.guardar(pago("PAG-1", EstadoPago.APROBADO))
        sesion.add(
            PagoDB(**RepositorioPagosPostgres._a_persistencia(pago("PAG-2", EstadoPago.APROBADO)))
        )
        sesion.commit()
    monkeypatch.setattr(database, "engine", engine)

    database._crear_indice_pago_aprobado(inspect(engine))

    assert "No se pudo crear uq_pagos_cotizacion_aprobado" in caplog.text
    engine.dispose()
