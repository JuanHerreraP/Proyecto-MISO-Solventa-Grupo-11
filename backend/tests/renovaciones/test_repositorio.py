"""Renovaciones, pólizas y cancelación sobre la base de datos (SQLite en memoria)."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cotizaciones.repositorio import RepositorioCotizacionesEnMemoria
from app.cotizaciones.servicio_personalizacion import ServicioPersonalizacionCotizacion
from app.desembolsos.modelos_db import DesembolsoDB
from app.desembolsos.repositorio import RepositorioDesembolsosPostgres
from app.pagos.repositorio import RepositorioPagosEnMemoria
from app.perfilamiento.enriquecimiento.memoria import RepositorioConsentimientosEnMemoria
from app.perfilamiento.repositorio import RepositorioPerfilesEnMemoria
from app.polizas.cancelacion import ServicioCancelaciones
from app.polizas.dominio.renovacion import EstadoRenovacion
from app.polizas.modelos_db import CancelacionDB, PolizaDB, RenovacionDB
from app.polizas.renovacion import ServicioRenovaciones
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.polizas.repositorio_cancelaciones import RepositorioCancelacionesPostgres
from app.polizas.repositorio_renovaciones import (
    RenovacionConcurrente,
    RepositorioRenovacionesPostgres,
)
from app.siniestros.modelos_db import SiniestroDB
from app.siniestros.repositorio import RepositorioSiniestrosPostgres
from tests.cancelaciones.fabrica import solicitud
from tests.endosos.fabrica import cotizacion
from tests.renovaciones.fabrica import (
    AHORA,
    DATOS_VIDA,
    POLIZA,
    TITULAR,
    Reloj,
    poliza,
)
from tests.renovaciones.test_dominio import renovacion


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for tabla in (PolizaDB, RenovacionDB, CancelacionDB, SiniestroDB, DesembolsoDB):
        tabla.__table__.create(engine)
    with sessionmaker(bind=engine)() as sesion:
        yield sesion
    engine.dispose()


def servicio_renovaciones(db, cotizaciones, reloj=None) -> ServicioRenovaciones:
    return ServicioRenovaciones(
        RepositorioPolizasPostgres(db),
        RepositorioRenovacionesPostgres(db),
        cotizaciones,
        ServicioPersonalizacionCotizacion(
            RepositorioPerfilesEnMemoria(), RepositorioConsentimientosEnMemoria()
        ),
        RepositorioPagosEnMemoria(),
        reloj=reloj or Reloj(),
    )


def test_crear_y_leer_una_renovacion_conserva_todos_los_campos(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    repo = RepositorioRenovacionesPostgres(db)
    original = renovacion(clave_idempotencia="k-1", ip_solicitante="10.0.0.1")

    repo.crear(original)
    db.expire_all()

    assert repo.obtener("REN-1") == original
    assert repo.por_cotizacion("COT-REN-1") == original
    assert repo.por_clave(POLIZA, "k-1") == original
    assert repo.por_clave(POLIZA, "otra") is None
    assert repo.por_poliza(POLIZA) == [original]
    assert repo.obtener("REN-NO") is None


def test_dos_renovaciones_del_mismo_periodo_chocan(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    repo = RepositorioRenovacionesPostgres(db)
    repo.crear(renovacion())

    with pytest.raises(RenovacionConcurrente):
        repo.crear(renovacion())
    with pytest.raises(RenovacionConcurrente):
        repo.crear(renovacion(renovacion_id="REN-2", cotizacion_id="COT-REN-2"))  # mismo periodo

    assert len(repo.por_poliza(POLIZA)) == 1  # la sesión sigue usable


def test_aplicar_guarda_la_renovacion_y_la_poliza_juntas_y_es_idempotente(db) -> None:
    polizas = RepositorioPolizasPostgres(db)
    polizas.guardar(poliza())
    repo = RepositorioRenovacionesPostgres(db)
    repo.crear(renovacion())
    aplicada = renovacion(estado=EstadoRenovacion.APLICADA, pago_id="PAG-1", aplicada_en=AHORA)
    renovada = poliza().model_copy(
        update={
            "fecha_inicio": date(2027, 1, 1),
            "fecha_fin": date(2027, 12, 31),
            "prima_total": Decimal("420000.00"),
        }
    )

    assert repo.aplicar(aplicada, renovada) is True
    db.expire_all()

    guardada = polizas.obtener(POLIZA)
    assert (guardada.fecha_inicio, guardada.fecha_fin) == (date(2027, 1, 1), date(2027, 12, 31))
    assert guardada.prima_total == Decimal("420000.00")
    assert repo.obtener("REN-1").estado is EstadoRenovacion.APLICADA
    assert repo.obtener("REN-1").aplicada_en == AHORA
    # Una segunda aplicación no cambia nada.
    assert (
        repo.aplicar(aplicada, renovada.model_copy(update={"prima_total": Decimal("1.00")}))
        is False
    )
    assert polizas.obtener(POLIZA).prima_total == Decimal("420000.00")


def test_reemplazar_una_renovacion_pendiente_pero_no_una_aplicada(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    repo = RepositorioRenovacionesPostgres(db)
    repo.crear(renovacion())

    repo.reemplazar_pendiente(renovacion(cotizacion_id="COT-REN-NUEVA"))
    assert repo.obtener("REN-1").cotizacion_id == "COT-REN-NUEVA"

    aplicada = renovacion(estado=EstadoRenovacion.APLICADA, aplicada_en=AHORA)
    repo.aplicar(aplicada, poliza())
    with pytest.raises(RenovacionConcurrente):
        repo.reemplazar_pendiente(renovacion(cotizacion_id="COT-OTRA"))
    repo.marcar_no_aplicada(renovacion(estado=EstadoRenovacion.NO_APLICADA))
    assert repo.obtener("REN-1").estado is EstadoRenovacion.APLICADA


def test_marcar_no_aplicada_registra_el_motivo(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    repo = RepositorioRenovacionesPostgres(db)
    repo.crear(renovacion())

    repo.marcar_no_aplicada(
        renovacion(
            estado=EstadoRenovacion.NO_APLICADA, pago_id="PAG-1", motivo_no_aplicada="Se canceló."
        )
    )

    registro = repo.obtener("REN-1")
    assert registro.estado is EstadoRenovacion.NO_APLICADA
    assert registro.motivo_no_aplicada == "Se canceló."


def test_renovar_y_pagar_con_datos_reales_actualiza_la_poliza(db) -> None:
    RepositorioPolizasPostgres(db).guardar(poliza())
    cotizaciones = RepositorioCotizacionesEnMemoria()
    cotizaciones.guardar(cotizacion().model_copy(update={"datos_riesgo": DATOS_VIDA}))
    servicio = servicio_renovaciones(db, cotizaciones)

    creada, _ = servicio.iniciar(TITULAR, POLIZA, "k-1")
    repetida, creada_otra_vez = servicio.iniciar(TITULAR, POLIZA, "k-1")
    assert creada_otra_vez is False and repetida == creada

    from app.pagos.modelos import EstadoPago, MetodoPago, Pago

    pago = Pago(
        pago_id="PAG-1",
        cotizacion_id=creada.cotizacion_id,
        cliente_id=TITULAR.actor_id,
        idempotency_key="llave-0001",
        huella_solicitud="0" * 64,
        metodo=MetodoPago.TARJETA,
        monto=creada.prima_total,
        moneda="COP",
        estado=EstadoPago.APROBADO,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )
    servicio.aplicar_pago(pago)
    db.expire_all()

    renovada = RepositorioPolizasPostgres(db).obtener(POLIZA)
    assert (renovada.fecha_inicio, renovada.fecha_fin) == (date(2027, 1, 1), date(2027, 12, 31))
    assert renovada.prima_total == Decimal("420000.00")


def test_cancelar_una_poliza_renovada_con_anticipacion_devuelve_los_dos_periodos(db) -> None:
    polizas = RepositorioPolizasPostgres(db)
    polizas.guardar(poliza())
    repo = RepositorioRenovacionesPostgres(db)
    repo.crear(renovacion())
    repo.aplicar(
        renovacion(estado=EstadoRenovacion.APLICADA, pago_id="PAG-1", aplicada_en=AHORA),
        poliza().model_copy(
            update={
                "fecha_inicio": date(2027, 1, 1),
                "fecha_fin": date(2027, 12, 31),
                "prima_total": Decimal("420000.00"),
            }
        ),
    )
    cotizaciones = RepositorioCotizacionesEnMemoria()
    cotizaciones.guardar(cotizacion())
    cancelaciones = ServicioCancelaciones(
        polizas,
        RepositorioCancelacionesPostgres(db),
        RepositorioSiniestrosPostgres(db),
        RepositorioDesembolsosPostgres(db),
        cotizaciones,
        repo,
        reloj=Reloj(),
    )

    propuesta, _ = cancelaciones.consultar(TITULAR, POLIZA)

    # Periodo en curso (hoy 10-dic): 150.000 x 21/365 = 8.630,14. El periodo pagado de 2027
    # aún no empieza y se devuelve completo: 420.000.
    assert propuesta.saldo_estimado == Decimal("428630.14")
    assert propuesta.prima_total == Decimal("570000.00")
    assert propuesta.dias_totales == 730
    assert propuesta.dias_no_transcurridos == 21 + 365

    cancelacion, _ = cancelaciones.confirmar(TITULAR, POLIZA, solicitud())

    assert cancelacion.saldo_estimado == Decimal("428630.14")
    assert polizas.obtener(POLIZA).estado.value == "CANCELADA"
