from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError

from app.identidad import auditoria
from app.identidad.auditoria import (
    TipoEventoAuth,
)


class FakeSession:
    def __init__(self):
        self.objeto_agregado = None
        self.commit_llamado = False
        self.rollback_llamado = False
        self.close_llamado = False

    def add(self, objeto):
        self.objeto_agregado = objeto

    def commit(self):
        self.commit_llamado = True

    def rollback(self):
        self.rollback_llamado = True

    def close(self):
        self.close_llamado = True


def _request():
    return SimpleNamespace(
        client=SimpleNamespace(host="192.168.1.20"),
        headers={"user-agent": "Mozilla/5.0 pytest"},
    )


def test_registra_evento_exitosamente(
    monkeypatch,
):
    session = FakeSession()

    monkeypatch.setattr(
        auditoria,
        "SessionLocal",
        lambda: session,
    )

    usuario_id = uuid4()

    auditoria.registrar_evento_auth(
        tipo_evento=(TipoEventoAuth.LOGIN_SUCCESS),
        exitoso=True,
        usuario_id=usuario_id,
        email="ANA@GMAIL.COM",
        detalle="Inicio exitoso",
        request=_request(),
    )

    evento = session.objeto_agregado

    assert evento is not None

    assert evento.tipo_evento == "LOGIN_SUCCESS"

    assert evento.exitoso is True

    assert evento.usuario_id == usuario_id

    assert evento.email == "ana@gmail.com"

    assert evento.ip == "192.168.1.20"

    assert evento.user_agent == "Mozilla/5.0 pytest"

    assert evento.detalle == "Inicio exitoso"

    assert session.commit_llamado is True

    assert session.close_llamado is True

    def test_registra_evento_sin_usuario(
        monkeypatch,
    ):
        session = FakeSession()

        monkeypatch.setattr(
            auditoria,
            "SessionLocal",
            lambda: session,
        )

        auditoria.registrar_evento_auth(
            tipo_evento=(TipoEventoAuth.TOKEN_REQUIRED),
            exitoso=False,
            detalle="TOKEN_REQUIRED",
            request=_request(),
        )

        evento = session.objeto_agregado

        assert evento.usuario_id is None
        assert evento.email is None

        assert evento.tipo_evento == "TOKEN_REQUIRED"

        assert evento.exitoso is False


def test_usuario_id_invalido_no_rompe_auditoria(
    monkeypatch,
):
    session = FakeSession()

    monkeypatch.setattr(
        auditoria,
        "SessionLocal",
        lambda: session,
    )

    auditoria.registrar_evento_auth(
        tipo_evento=(TipoEventoAuth.ACCESS_DENIED),
        exitoso=False,
        usuario_id="esto-no-es-uuid",
        email="ana@gmail.com",
        detalle="ACCESS_DENIED",
        request=_request(),
    )

    evento = session.objeto_agregado

    assert evento.usuario_id is None

    assert evento.email == "ana@gmail.com"

    assert session.commit_llamado is True


class FakeSessionConError(FakeSession):
    def commit(self):
        raise SQLAlchemyError("BD auditoría caída")


def test_error_de_auditoria_no_se_propaga(
    monkeypatch,
):
    session = FakeSessionConError()

    monkeypatch.setattr(
        auditoria,
        "SessionLocal",
        lambda: session,
    )

    # Si registrar_evento_auth lanza
    # excepción, esta prueba falla.
    auditoria.registrar_evento_auth(
        tipo_evento=(TipoEventoAuth.LOGIN_FAILED),
        exitoso=False,
        email="ana@gmail.com",
        detalle="INVALID_CREDENTIALS",
        request=_request(),
    )

    assert session.rollback_llamado is True

    assert session.close_llamado is True


def test_evento_puede_registrarse_sin_request(
    monkeypatch,
):
    session = FakeSession()

    monkeypatch.setattr(
        auditoria,
        "SessionLocal",
        lambda: session,
    )

    auditoria.registrar_evento_auth(
        tipo_evento=(TipoEventoAuth.LOGIN_FAILED),
        exitoso=False,
        email="ana@gmail.com",
        detalle="INVALID_CREDENTIALS",
        request=None,
    )

    evento = session.objeto_agregado

    assert evento.ip is None
    assert evento.user_agent is None

    assert session.commit_llamado is True


def test_evento_no_contiene_campos_sensibles(
    monkeypatch,
):
    session = FakeSession()

    monkeypatch.setattr(
        auditoria,
        "SessionLocal",
        lambda: session,
    )

    auditoria.registrar_evento_auth(
        tipo_evento=(TipoEventoAuth.LOGIN_SUCCESS),
        exitoso=True,
        email="ana@gmail.com",
        detalle="Inicio de sesión exitoso.",
        request=_request(),
    )

    evento = session.objeto_agregado

    assert not hasattr(evento, "password")

    assert not hasattr(evento, "access_token")

    assert not hasattr(evento, "refresh_token")
