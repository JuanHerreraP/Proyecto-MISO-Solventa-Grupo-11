from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import jwt
import pytest

from app.identidad import tokens


def _crear_llaves():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_pem = (
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    return private_pem, public_pem


def test_access_token_usa_rs256(
    tmp_path,
    monkeypatch,
):
    private_pem, public_pem = (
        _crear_llaves()
    )

    private_path = (
        tmp_path / "private_key.pem"
    )

    private_path.write_bytes(
        private_pem
    )

    monkeypatch.setattr(
        tokens,
        "PRIVATE_KEY_PATH",
        private_path,
    )

    token = tokens.crear_access_token(
        usuario_id="usuario-123",
        email="ana@gmail.com",
        rol="CLIENTE",
    )

    header = jwt.get_unverified_header(
        token
    )

    assert header["alg"] == "RS256"


def test_access_token_contiene_claims_del_usuario(
    tmp_path,
    monkeypatch,
):
    private_pem, public_pem = (
        _crear_llaves()
    )

    private_path = (
        tmp_path / "private_key.pem"
    )

    private_path.write_bytes(
        private_pem
    )

    monkeypatch.setattr(
        tokens,
        "PRIVATE_KEY_PATH",
        private_path,
    )

    token = tokens.crear_access_token(
        usuario_id="usuario-123",
        email="ana@gmail.com",
        rol="CLIENTE",
    )

    payload = jwt.decode(
        token,
        public_pem,
        algorithms=["RS256"],
    )

    assert payload["sub"] == "usuario-123"
    assert payload["email"] == "ana@gmail.com"
    assert payload["rol"] == "CLIENTE"
    assert payload["type"] == "access"


def test_access_token_expira_en_30_minutos(
    tmp_path,
    monkeypatch,
):
    private_pem, public_pem = (
        _crear_llaves()
    )

    private_path = (
        tmp_path / "private_key.pem"
    )

    private_path.write_bytes(
        private_pem
    )

    monkeypatch.setattr(
        tokens,
        "PRIVATE_KEY_PATH",
        private_path,
    )

    monkeypatch.setattr(
        tokens,
        "ACCESS_TOKEN_MINUTES",
        30,
    )

    token = tokens.crear_access_token(
        usuario_id="usuario-123",
        email="ana@gmail.com",
        rol="CLIENTE",
    )

    payload = jwt.decode(
        token,
        public_pem,
        algorithms=["RS256"],
    )

    diferencia = (
        payload["exp"]
        - payload["iat"]
    )

    assert diferencia == 1800


def test_token_no_valida_con_otra_llave(
    tmp_path,
    monkeypatch,
):
    private_pem, public_pem = (
        _crear_llaves()
    )

    _, public_key_incorrecta = (
        _crear_llaves()
    )

    private_path = (
        tmp_path / "private_key.pem"
    )

    private_path.write_bytes(
        private_pem
    )

    monkeypatch.setattr(
        tokens,
        "PRIVATE_KEY_PATH",
        private_path,
    )

    token = tokens.crear_access_token(
        usuario_id="usuario-123",
        email="ana@gmail.com",
        rol="CLIENTE",
    )

    with pytest.raises(
        jwt.InvalidSignatureError
    ):
        jwt.decode(
            token,
            public_key_incorrecta,
            algorithms=["RS256"],
        )