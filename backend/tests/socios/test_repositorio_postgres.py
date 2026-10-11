from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.socios.dominio.auditoria import AccionAuditoria, RegistroAuditoriaSocio
from app.socios.dominio.modelos import EstadoSocio, SocioDistribucion
from app.socios.modelos_db import EventoAuditoriaSocioDB, SocioDistribucionDB
from app.socios.repositorio import (
    RepositorioAuditoriaSociosPostgres,
    RepositorioSociosPostgres,
)
from tests.socios.fabrica import solicitud_alta


def test_persiste_socio_tenant_y_auditoria() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SocioDistribucionDB.__table__.create(engine)
    EventoAuditoriaSocioDB.__table__.create(engine)
    fecha = datetime(2026, 10, 8, tzinfo=timezone.utc)
    socio = SocioDistribucion(
        **solicitud_alta().model_dump(),
        socio_id="SOCIO-001",
        tenant_id="TENANT-001",
        estado=EstadoSocio.ACTIVO,
        creado_en=fecha,
        actualizado_en=fecha,
    )

    with Session(engine) as db:
        repositorio = RepositorioSociosPostgres(db)
        auditoria = RepositorioAuditoriaSociosPostgres(db)
        repositorio.guardar(socio)
        auditoria.registrar(
            RegistroAuditoriaSocio(
                auditoria_id="AUD-001",
                socio_id=socio.socio_id,
                actor_id="ingeniero-01",
                accion=AccionAuditoria.ALTA,
                campos_modificados=["tenant_id"],
                fecha=fecha,
            )
        )

        persistido = repositorio.obtener(socio.socio_id)
        eventos = auditoria.listar_por_socio(socio.socio_id)

    assert persistido.socio_id == socio.socio_id
    assert persistido.tenant_id == socio.tenant_id
    assert eventos[0].actor_id == "ingeniero-01"
