"""HU02 (BPM-23): renovación, rotación y cierre de sesión en el servicio de identidad."""

import jwt
import pytest

from app.identidad import tokens
from app.identidad.repositorio import RepositorioSesionesPostgres, RepositorioUsuariosPostgres
from app.identidad.servicio import (
    ServicioIdentidad,
    SesionInvalidaError,
    SesionReutilizadaError,
    UsuarioInactivoError,
)
from app.identidad.tokens import TokenExpiradoError, TokenInvalidoError
from tests.identidad.tests_sesion.conftest import PASSWORD, crear_usuario


@pytest.fixture
def servicio(db):
    return ServicioIdentidad(
        repositorio=RepositorioUsuariosPostgres(db),
        repositorio_sesiones=RepositorioSesionesPostgres(db),
    )


def _jti(token: str) -> str:
    return jwt.decode(token, options={"verify_signature": False})["jti"]


def test_login_registra_la_sesion_del_refresh_token(servicio, db):
    usuario = crear_usuario(db)

    respuesta = servicio.autenticar_usuario(email=usuario.email, password=PASSWORD)

    sesion = RepositorioSesionesPostgres(db).buscar(_jti(respuesta.refresh_token))
    assert sesion is not None
    assert str(sesion.usuario_id) == str(usuario.id)
    assert sesion.revocada is False


def test_refresh_entrega_un_par_nuevo_y_revoca_el_anterior(servicio, db):
    usuario = crear_usuario(db)
    login = servicio.autenticar_usuario(email=usuario.email, password=PASSWORD)

    renovado = servicio.renovar_sesion(login.refresh_token)

    assert renovado.refresh_token != login.refresh_token
    assert tokens.validar_access_token(renovado.access_token)["sub"] == str(usuario.id)
    anterior = RepositorioSesionesPostgres(db).buscar(_jti(login.refresh_token))
    assert anterior.revocada is True
    assert anterior.motivo_revocacion == "ROTACION"
    assert anterior.reemplazada_por == _jti(renovado.refresh_token)


def test_reusar_un_refresh_rotado_cierra_todas_las_sesiones(servicio, db):
    usuario = crear_usuario(db)
    login = servicio.autenticar_usuario(email=usuario.email, password=PASSWORD)
    renovado = servicio.renovar_sesion(login.refresh_token)

    with pytest.raises(SesionReutilizadaError) as error:
        servicio.renovar_sesion(login.refresh_token)

    assert error.value.usuario_id == str(usuario.id)
    vigente = RepositorioSesionesPostgres(db).buscar(_jti(renovado.refresh_token))
    assert vigente.revocada is True
    assert vigente.motivo_revocacion == "REUTILIZACION_DETECTADA"


def test_refresh_expirado_se_rechaza(servicio, db, monkeypatch):
    usuario = crear_usuario(db)
    monkeypatch.setattr(tokens, "REFRESH_TOKEN_DAYS", -1)
    login = servicio.autenticar_usuario(email=usuario.email, password=PASSWORD)

    with pytest.raises(TokenExpiradoError):
        servicio.renovar_sesion(login.refresh_token)


def test_refresh_sin_jti_no_es_una_sesion_valida(servicio, db):
    usuario = crear_usuario(db)
    antiguo = tokens.crear_access_token(str(usuario.id), usuario.email, usuario.rol)
    sin_jti = jwt.encode(
        {**jwt.decode(antiguo, options={"verify_signature": False}), "type": "refresh"},
        tokens.PRIVATE_KEY_PATH.read_text(),
        algorithm="RS256",
    )

    with pytest.raises(SesionInvalidaError):
        servicio.renovar_sesion(sin_jti)


def test_access_token_no_sirve_como_refresh(servicio, db):
    usuario = crear_usuario(db)
    login = servicio.autenticar_usuario(email=usuario.email, password=PASSWORD)

    with pytest.raises(TokenInvalidoError):
        servicio.renovar_sesion(login.access_token)


def test_refresh_de_otro_usuario_no_se_acepta(servicio, db):
    ana = crear_usuario(db, email="ana@gmail.com")
    luis = crear_usuario(db, email="luis@gmail.com")
    login_ana = servicio.autenticar_usuario(email=ana.email, password=PASSWORD)
    payload = jwt.decode(login_ana.refresh_token, options={"verify_signature": False})
    suplantado = jwt.encode(
        {**payload, "sub": str(luis.id)},
        tokens.PRIVATE_KEY_PATH.read_text(),
        algorithm="RS256",
    )

    with pytest.raises(SesionInvalidaError):
        servicio.renovar_sesion(suplantado)


def test_usuario_inactivo_no_puede_renovar(servicio, db):
    usuario = crear_usuario(db)
    login = servicio.autenticar_usuario(email=usuario.email, password=PASSWORD)
    usuario.activo = False
    db.commit()

    with pytest.raises(UsuarioInactivoError):
        servicio.renovar_sesion(login.refresh_token)

    sesion = RepositorioSesionesPostgres(db).buscar(_jti(login.refresh_token))
    assert sesion.revocada is True


def test_logout_revoca_y_el_refresh_ya_no_sirve(servicio, db):
    usuario = crear_usuario(db)
    login = servicio.autenticar_usuario(email=usuario.email, password=PASSWORD)

    assert servicio.cerrar_sesion(login.refresh_token) == str(usuario.id)

    with pytest.raises(SesionInvalidaError):
        servicio.renovar_sesion(login.refresh_token)


def test_logout_es_idempotente(servicio, db):
    usuario = crear_usuario(db)
    login = servicio.autenticar_usuario(email=usuario.email, password=PASSWORD)

    servicio.cerrar_sesion(login.refresh_token)
    servicio.cerrar_sesion(login.refresh_token)

    sesion = RepositorioSesionesPostgres(db).buscar(_jti(login.refresh_token))
    assert sesion.motivo_revocacion == "LOGOUT"


def test_logout_con_refresh_expirado_no_falla(servicio, db, monkeypatch):
    usuario = crear_usuario(db)
    monkeypatch.setattr(tokens, "REFRESH_TOKEN_DAYS", -1)
    login = servicio.autenticar_usuario(email=usuario.email, password=PASSWORD)

    assert servicio.cerrar_sesion(login.refresh_token) is None


def test_renovar_y_cerrar_requieren_repositorio_de_sesiones(db):
    servicio = ServicioIdentidad(repositorio=RepositorioUsuariosPostgres(db))

    with pytest.raises(RuntimeError):
        servicio.renovar_sesion("x")
    with pytest.raises(RuntimeError):
        servicio.cerrar_sesion("x")
