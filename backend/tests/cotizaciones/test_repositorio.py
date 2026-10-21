from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.cotizaciones.dominio.modelos import Cotizacion, EstadoCotizacion, RamoSeguro
from app.cotizaciones.modelos_db import CotizacionDB
from app.cotizaciones.repositorio import (
    RepositorioCotizacionesEnMemoria,
    RepositorioCotizacionesPostgres,
)


def crear_cotizacion(
    cotizacion_id: str = "COT-001",
    cliente_id: str = "CLI-001",
    creada_en: datetime | None = None,
    *,
    asesor_id: str | None = None,
    socio_id: str | None = None,
    tenant_id: str | None = None,
) -> Cotizacion:
    fecha = creada_en or datetime(2027, 1, 10, tzinfo=UTC)
    return Cotizacion(
        cotizacion_id=cotizacion_id,
        cliente_id=cliente_id,
        ramo=RamoSeguro.VIDA,
        datos_riesgo={
            "fecha_nacimiento": "1990-05-20",
            "valor_asegurado": "100000000.00",
            "meses_cobertura": 12,
            "fumador": False,
        },
        estado=EstadoCotizacion.VIGENTE,
        prima_total=Decimal("504000.00"),
        cobertura_principal={
            "codigo": "FALLECIMIENTO",
            "nombre": "Cobertura por fallecimiento",
            "suma_asegurada": Decimal("100000000.00"),
        },
        perfil_riesgo_id="PERFIL-001",
        asesor_id=asesor_id,
        socio_id=socio_id,
        tenant_id=tenant_id,
        creada_en=fecha,
        vigente_hasta=fecha + timedelta(days=7),
    )


def test_repositorio_en_memoria_guarda_una_copia_independiente() -> None:
    repositorio = RepositorioCotizacionesEnMemoria()
    original = crear_cotizacion()

    repositorio.guardar(original)
    consultada = repositorio.obtener(original.cotizacion_id)

    assert consultada == original
    assert consultada is not original


def test_repositorio_en_memoria_lista_solo_las_cotizaciones_del_cliente() -> None:
    repositorio = RepositorioCotizacionesEnMemoria()
    repositorio.guardar(crear_cotizacion("COT-ANTERIOR"))
    repositorio.guardar(
        crear_cotizacion(
            "COT-RECIENTE",
            creada_en=datetime(2027, 1, 11, tzinfo=UTC),
        )
    )
    repositorio.guardar(crear_cotizacion("COT-OTRO", cliente_id="CLI-002"))

    cotizaciones = repositorio.listar_por_cliente("CLI-001")

    assert [cotizacion.cotizacion_id for cotizacion in cotizaciones] == [
        "COT-RECIENTE",
        "COT-ANTERIOR",
    ]


def test_postgres_persiste_y_reconstruye_la_cotizacion_completa() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    CotizacionDB.__table__.create(engine)
    original = crear_cotizacion()

    with Session(engine) as db:
        repositorio = RepositorioCotizacionesPostgres(db)
        repositorio.guardar(original)
        consultada = repositorio.obtener(original.cotizacion_id)

    assert consultada == original
    assert consultada.prima_total == Decimal("504000.00")
    assert consultada.creada_en.tzinfo is not None


@pytest.mark.parametrize(
    "contexto",
    [
        {"asesor_id": "ASESOR-001"},
        {"socio_id": "SOCIO-001", "tenant_id": "TENANT-001"},
    ],
)
def test_postgres_conserva_el_contexto_de_autorizacion(
    contexto: dict[str, str],
) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    CotizacionDB.__table__.create(engine)
    original = crear_cotizacion(**contexto)

    with Session(engine) as db:
        repositorio = RepositorioCotizacionesPostgres(db)
        repositorio.guardar(original)
        consultada = repositorio.obtener(original.cotizacion_id)

    assert consultada is not None
    assert consultada.asesor_id == contexto.get("asesor_id")
    assert consultada.socio_id == contexto.get("socio_id")
    assert consultada.tenant_id == contexto.get("tenant_id")


def test_postgres_lista_por_cliente_de_mas_reciente_a_mas_antigua() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    CotizacionDB.__table__.create(engine)

    with Session(engine) as db:
        repositorio = RepositorioCotizacionesPostgres(db)
        repositorio.guardar(crear_cotizacion("COT-ANTERIOR"))
        repositorio.guardar(
            crear_cotizacion(
                "COT-RECIENTE",
                creada_en=datetime(2027, 1, 11, tzinfo=UTC),
            )
        )
        repositorio.guardar(crear_cotizacion("COT-OTRO", cliente_id="CLI-002"))

        cotizaciones = repositorio.listar_por_cliente("CLI-001")

    assert [cotizacion.cotizacion_id for cotizacion in cotizaciones] == [
        "COT-RECIENTE",
        "COT-ANTERIOR",
    ]


def test_postgres_retorna_none_para_una_cotizacion_inexistente() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    CotizacionDB.__table__.create(engine)

    with Session(engine) as db:
        repositorio = RepositorioCotizacionesPostgres(db)

        assert repositorio.obtener("COT-INEXISTENTE") is None
