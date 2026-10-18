import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.perfilamiento.enriquecimiento.cliente_http import crear_cliente
from app.perfilamiento.enriquecimiento.tokens_proveedores import (
    AutenticacionProveedor,
    crear_token_proveedor,
)


def _crear_llaves() -> tuple[str, str]:
    llave_privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    privada = llave_privada.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    publica = llave_privada.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return privada.decode(), publica.decode()


def _proveedor_protegido(llave_publica: str, audiencia: str):
    def responder(request: httpx.Request) -> httpx.Response:
        try:
            esquema, token = request.headers["Authorization"].split(" ", 1)
            if esquema != "Bearer":
                raise jwt.InvalidTokenError("Esquema de autenticación inválido.")
            payload = jwt.decode(
                token,
                llave_publica,
                algorithms=["RS256"],
                issuer="solventa",
                audience=audiencia,
                options={"require": ["iss", "sub", "aud", "iat", "exp", "jti"]},
            )
            if payload.get("type") != "provider_access":
                raise jwt.InvalidTokenError("Tipo de token inválido.")
        except (KeyError, ValueError, jwt.PyJWTError):
            return httpx.Response(401, json={"detail": "UNAUTHORIZED"})
        return httpx.Response(200, json={})

    return responder


def test_token_proveedor_esta_firmado_y_contiene_claims_requeridos() -> None:
    privada, publica = _crear_llaves()
    ahora = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)

    token = crear_token_proveedor(
        llave_privada=privada,
        emisor="solventa",
        audiencia="open-finance",
        ahora=ahora,
    )
    payload = jwt.decode(
        token,
        publica,
        algorithms=["RS256"],
        issuer="solventa",
        audience="open-finance",
        options={"verify_exp": False},
    )

    assert jwt.get_unverified_header(token)["alg"] == "RS256"
    assert payload["iss"] == "solventa"
    assert payload["sub"] == "servicio-perfilamiento"
    assert payload["aud"] == "open-finance"
    assert payload["type"] == "provider_access"
    assert payload["exp"] - payload["iat"] == 60
    assert payload["jti"]


def test_cada_token_proveedor_tiene_identificador_unico() -> None:
    privada, _ = _crear_llaves()
    parametros = {
        "llave_privada": privada,
        "emisor": "solventa",
        "audiencia": "open-data",
    }

    primero = jwt.decode(
        crear_token_proveedor(**parametros),
        options={"verify_signature": False},
    )
    segundo = jwt.decode(
        crear_token_proveedor(**parametros),
        options={"verify_signature": False},
    )

    assert primero["jti"] != segundo["jti"]


@pytest.mark.parametrize("campo", ["llave_privada", "emisor", "audiencia", "servicio"])
def test_token_proveedor_rechaza_configuracion_incompleta(campo: str) -> None:
    privada, _ = _crear_llaves()
    parametros = {
        "llave_privada": privada,
        "emisor": "solventa",
        "audiencia": "open-finance",
        "servicio": "servicio-perfilamiento",
    }
    parametros[campo] = ""

    with pytest.raises(ValueError, match="configuración completa"):
        crear_token_proveedor(**parametros)


def test_cliente_genera_un_token_firmado_para_cada_solicitud() -> None:
    privada, publica = _crear_llaves()
    tokens_enviados = []
    proveedor = _proveedor_protegido(publica, "open-finance")

    def responder(request: httpx.Request) -> httpx.Response:
        tokens_enviados.append(request.headers["Authorization"].removeprefix("Bearer "))
        return proveedor(request)

    cliente = crear_cliente(
        "https://proveedor.example",
        autenticacion=AutenticacionProveedor(
            llave_privada=privada,
            emisor="solventa",
            audiencia="open-finance",
        ),
        transporte=httpx.MockTransport(responder),
    )

    async def consultar() -> None:
        async with cliente:
            assert (await cliente.get("/primera")).status_code == 200
            assert (await cliente.get("/segunda")).status_code == 200

    asyncio.run(consultar())

    payloads = [
        jwt.decode(
            token,
            publica,
            algorithms=["RS256"],
            issuer="solventa",
            audience="open-finance",
        )
        for token in tokens_enviados
    ]
    assert len(payloads) == 2
    assert payloads[0]["jti"] != payloads[1]["jti"]


def test_proveedor_rechaza_todos_los_intentos_de_suplantacion() -> None:
    privada, publica = _crear_llaves()
    privada_atacante, _ = _crear_llaves()
    ahora = datetime.now(timezone.utc)
    token_valido = crear_token_proveedor(
        llave_privada=privada,
        emisor="solventa",
        audiencia="open-data",
    )
    intentos = [
        None,
        crear_token_proveedor(
            llave_privada=privada_atacante,
            emisor="solventa",
            audiencia="open-data",
        ),
        crear_token_proveedor(
            llave_privada=privada,
            emisor="solventa",
            audiencia="open-data",
            ahora=ahora - timedelta(minutes=2),
        ),
        crear_token_proveedor(
            llave_privada=privada,
            emisor="solventa",
            audiencia="otro-proveedor",
        ),
        f"{token_valido}alterado",
    ]
    transporte = httpx.MockTransport(_proveedor_protegido(publica, "open-data"))

    async def atacar() -> list[int]:
        async with httpx.AsyncClient(
            base_url="https://proveedor.example",
            transport=transporte,
        ) as cliente_atacante:
            respuestas = []
            for token in intentos:
                encabezados = {"Authorization": f"Bearer {token}"} if token else {}
                respuesta = await cliente_atacante.get("/datos", headers=encabezados)
                respuestas.append(respuesta.status_code)
            return respuestas

    assert asyncio.run(atacar()) == [401, 401, 401, 401, 401]
