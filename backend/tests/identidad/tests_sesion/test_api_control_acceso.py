"""Control de acceso real con JWT y auditoría persistida, sin overrides de seguridad."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api import enriquecimiento, perfilamiento
from app.identidad import auditoria
from app.identidad.config import get_identity_verification_provider
from app.identidad.modelos import Rol, VerificationStatus
from app.identidad.modelos_db import EventoAutenticacionDB
from app.identidad.tokens import crear_access_token
from app.infraestructura.database import get_db
from app.main import app
from app.perfilamiento.repositorio import RepositorioPerfilesEnMemoria
from app.perfilamiento.servicio import ServicioPerfilamiento
from tests.identidad.tests_sesion.conftest import crear_usuario
from tests.perfilamiento.fabrica import senales


@pytest.fixture
def api(fabrica_sesiones, monkeypatch, db):
    EventoAutenticacionDB.__table__.create(db.get_bind())
    monkeypatch.setattr(auditoria, "SessionLocal", fabrica_sesiones)

    def obtener_db():
        with fabrica_sesiones() as sesion:
            yield sesion

    class Provider:
        def verify(self, solicitud):
            return SimpleNamespace(
                verification_id="TEST-KYC",
                status=VerificationStatus.APPROVED,
                risk_score=0.1,
                checked_at=datetime.now(timezone.utc),
            )

    app.dependency_overrides[get_db] = obtener_db
    app.dependency_overrides[get_identity_verification_provider] = Provider
    servicio = ServicioPerfilamiento(RepositorioPerfilesEnMemoria())
    app.dependency_overrides[perfilamiento.obtener_servicio] = lambda: servicio
    enriquecimiento.obtener_consentimientos.cache_clear()
    enriquecimiento.obtener_servicio.cache_clear()
    try:
        yield TestClient(app), servicio
    finally:
        app.dependency_overrides.clear()
        enriquecimiento.obtener_consentimientos.cache_clear()
        enriquecimiento.obtener_servicio.cache_clear()


def identidad(db, rol):
    usuario = crear_usuario(db)
    usuario.rol = rol.value
    db.commit()
    token = crear_access_token(str(usuario.id), usuario.email, rol.value)
    return usuario, {"Authorization": f"Bearer {token}"}


def eventos(db):
    return db.scalars(select(EventoAutenticacionDB)).all()


@pytest.mark.parametrize("rol", list(Rol))
def test_matriz_permisos_y_auditoria(api, db, rol):
    cliente, servicio = api
    usuario, headers = identidad(db, rol)
    servicio.generar_perfil(senales(cliente_id=str(usuario.id)))
    consulta = cliente.get(f"/api/v1/perfiles-riesgo/{usuario.id}", headers=headers)
    permitido = rol in {Rol.ANALISTA_RIESGOS, Rol.SERVICIO_INTERNO}
    assert consulta.status_code == (200 if permitido else 403)
    registro = eventos(db)[-1]
    assert str(registro.usuario_id) == str(usuario.id)
    assert registro.exitoso is permitido
    assert registro.tipo_evento == ("SENSITIVE_OPERATION" if permitido else "ACCESS_DENIED")
    assert f"/api/v1/perfiles-riesgo/{usuario.id}" in registro.detalle
    assert len(eventos(db)) == 1  # Una sola entrada, aunque la dependencia ya audite.


@pytest.mark.parametrize("rol", list(Rol))
def test_matriz_generacion_perfil(api, db, rol):
    cliente, _ = api
    usuario, headers = identidad(db, rol)
    respuesta = cliente.post(
        "/api/v1/perfiles-riesgo",
        headers=headers,
        json=senales(cliente_id=str(usuario.id)).model_dump(mode="json"),
    )
    assert respuesta.status_code == (
        201 if rol in {Rol.ASESOR_VENTAS, Rol.SERVICIO_INTERNO} else 403
    )


def test_cliente_no_puede_operar_sobre_otro_cliente(api, db):
    cliente, servicio = api
    usuario, headers = identidad(db, Rol.CLIENTE)
    servicio.generar_perfil(senales(cliente_id="otro-cliente"))
    assert (
        cliente.get("/api/v1/perfiles-riesgo/otro-cliente/oferta", headers=headers).status_code
        == 403
    )
    consentimiento = {
        "consentimiento_id": "CONS-1",
        "cliente_id": "otro-cliente",
        "vence_en": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    }
    assert (
        cliente.post("/api/v1/consentimientos", json=consentimiento, headers=headers).status_code
        == 403
    )
    servicio.generar_perfil(senales(cliente_id=str(usuario.id)))
    assert (
        cliente.get(f"/api/v1/perfiles-riesgo/{usuario.id}/oferta", headers=headers).status_code
        == 200
    )
    consentimiento["cliente_id"] = str(usuario.id)
    assert (
        cliente.post("/api/v1/consentimientos", json=consentimiento, headers=headers).status_code
        == 201
    )
    assert [e.exitoso for e in eventos(db)] == [False, False, True, True]


@pytest.mark.parametrize("rol", list(Rol))
def test_kyc_directo_solo_servicio_interno(api, db, rol):
    cliente, _ = api
    _, headers = identidad(db, rol)
    respuesta = cliente.post(
        "/identidad/verificaciones",
        headers=headers,
        json={
            "customer_id": "CLI-1",
            "consent_id": "CONS-1",
            "document_type": "CC",
            "document_number": "123456789",
            "full_name": "Ana Perez",
            "birth_date": "1990-01-01",
        },
    )
    assert respuesta.status_code == (200 if rol == Rol.SERVICIO_INTERNO else 403)
    assert len(eventos(db)) == 1


@pytest.mark.parametrize(
    "ruta",
    [
        "/api/v1/auth/users",
        "/api/v1/perfiles-riesgo/otro/oferta",
        "/api/v1/enriquecimientos/otro",
        "/api/v1/socios/otro",
    ],
)
def test_sin_token_se_rechaza_y_audita(api, db, ruta):
    cliente, _ = api
    respuesta = cliente.get(ruta)
    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
    assert len(eventos(db)) == 1
    assert eventos(db)[0].exitoso is False


def test_usuario_invalido_en_jwt_no_produce_500(api, db):
    cliente, _ = api
    token = crear_access_token("no-es-un-uuid", "test@example.com", "SERVICIO_INTERNO")
    assert (
        cliente.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {token}"}).status_code
        == 401
    )
    assert len(eventos(db)) == 1


@pytest.mark.parametrize("rol", list(Rol))
def test_permisos_uniformes_en_los_demas_recursos(api, db, rol):
    cliente, servicio = api
    usuario, headers = identidad(db, rol)
    servicio.generar_perfil(senales(cliente_id=str(usuario.id)))
    operaciones = [
        ("GET", "/api/v1/auth/users", None, {Rol.SERVICIO_INTERNO}, 200),
        (
            "GET",
            f"/api/v1/perfiles-riesgo/{usuario.id}/oferta",
            None,
            {Rol.CLIENTE, Rol.ASESOR_VENTAS, Rol.ANALISTA_RIESGOS, Rol.SERVICIO_INTERNO},
            200,
        ),
        (
            "GET",
            f"/api/v1/enriquecimientos/{usuario.id}",
            None,
            {Rol.ANALISTA_RIESGOS, Rol.SERVICIO_INTERNO},
            404,
        ),
        (
            "POST",
            "/api/v1/enriquecimientos",
            {"cliente_id": str(usuario.id), "cotizacion_id": "COT"},
            {Rol.ASESOR_VENTAS, Rol.SERVICIO_INTERNO},
            409,
        ),
        (
            "POST",
            "/api/v1/consentimientos",
            {
                "cliente_id": str(usuario.id),
                "consentimiento_id": "CONS",
                "vence_en": "2999-01-01T00:00:00Z",
            },
            {Rol.CLIENTE, Rol.ASESOR_VENTAS, Rol.SERVICIO_INTERNO},
            201,
        ),
    ]
    for metodo, ruta, cuerpo, permitidos, exitoso in operaciones:
        cantidad = len(eventos(db))
        respuesta = cliente.request(metodo, ruta, json=cuerpo, headers=headers)
        assert respuesta.status_code == (exitoso if rol in permitidos else 403)
        if respuesta.status_code == 403:
            nuevos = eventos(db)[cantidad:]
            assert len(nuevos) == 1
            assert nuevos[0].tipo_evento == "ACCESS_DENIED"
            assert nuevos[0].usuario_id == usuario.id


def test_rechazo_de_scope_de_socio_se_audita_sin_secretos(api, db):
    from app.socios.dominio.catalogo import CodigoEndpoint
    from app.socios.dominio.credenciales import CredencialesSocio
    from app.socios.tokens import crear_access_token_socio

    cliente, _ = api
    credencial = CredencialesSocio(
        socio_id="SOCIO-PRUEBA",
        tenant_id="TENANT-PRUEBA",
        client_id="cliente-prueba",
        secret_hash="hash-no-publicar",
        scopes={CodigoEndpoint.COTIZACIONES_CREAR},
        creado_en=datetime.now(timezone.utc),
    )
    token, _ = crear_access_token_socio(credencial, credencial.scopes)
    respuesta = cliente.post(
        "/api/v1/autorizaciones/socios",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Scope": "polizas:emitir",
        },
    )
    assert respuesta.status_code == 403
    registro = eventos(db)[0]
    assert registro.tipo_evento == "ACCESS_DENIED"
    assert "socio:SOCIO-PRUEBA" in registro.detalle
    assert token not in registro.detalle
    assert "hash-no-publicar" not in registro.detalle


def test_cabecera_de_rol_no_eleva_privilegios(api, db):
    cliente, _ = api
    _, headers = identidad(db, Rol.CLIENTE)
    headers["X-Rol"] = "SERVICIO_INTERNO"
    assert cliente.get("/api/v1/auth/users", headers=headers).status_code == 403
    assert len(eventos(db)) == 1


def test_consulta_sensible_fallida_tambien_se_audita(api, db):
    cliente, _ = api
    usuario, headers = identidad(db, Rol.ANALISTA_RIESGOS)
    respuesta = cliente.get("/api/v1/perfiles-riesgo/inexistente", headers=headers)
    assert respuesta.status_code == 404
    registro = eventos(db)[0]
    assert registro.usuario_id == usuario.id
    assert registro.tipo_evento == "SENSITIVE_OPERATION"
    assert registro.exitoso is False
    assert "HTTP_404" in registro.detalle
