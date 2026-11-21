"""Adaptador de FCM: autenticación, formato del mensaje y clasificación de los errores.

Google se simula con `httpx.MockTransport`: no sale ninguna petición a la red.
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.notificaciones.canal import ConfiguracionPushInvalida
from app.notificaciones.fcm import (
    ALCANCE,
    CANAL_ANDROID,
    URL_TOKEN_POR_DEFECTO,
    CredencialesFCM,
    EnviadorPushFCM,
    cargar_credenciales,
)
from app.notificaciones.modelos import PushPendiente

AHORA = datetime(2026, 12, 10, 15, 0, tzinfo=UTC)
CORREO = "push@solventa-test.iam.gserviceaccount.com"


@pytest.fixture(scope="module")
def llaves():
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return (
        privada.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
        privada.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode(),
    )


class Reloj:
    def __init__(self):
        self.ahora = AHORA

    def __call__(self) -> datetime:
        return self.ahora

    def avanzar(self, **delta) -> None:
        self.ahora += timedelta(**delta)


class Google:
    """Servidor falso: el endpoint del token de acceso y el de envío de FCM."""

    def __init__(self, envio=None, acceso=None):
        self.peticiones_de_acceso: list[httpx.Request] = []
        self.peticiones_de_envio: list[httpx.Request] = []
        self._envio = envio or (lambda peticion: httpx.Response(200, json={"name": "mensaje"}))
        self._acceso = acceso

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        if str(peticion.url) == URL_TOKEN_POR_DEFECTO:
            self.peticiones_de_acceso.append(peticion)
            if self._acceso is not None:
                return self._acceso(peticion)
            numero = len(self.peticiones_de_acceso)
            return httpx.Response(
                200, json={"access_token": f"acceso-{numero}", "expires_in": 3600}
            )
        self.peticiones_de_envio.append(peticion)
        return self._envio(peticion)


def crear(llaves, google: Google | None = None, reloj: Reloj | None = None):
    google = google or Google()
    reloj = reloj or Reloj()
    credenciales = CredencialesFCM("solventa-test", CORREO, llaves[0])
    cliente = httpx.Client(transport=httpx.MockTransport(google))
    return EnviadorPushFCM(credenciales, cliente=cliente, reloj=reloj), google, reloj


def push(*tokens: str) -> PushPendiente:
    return PushPendiente(
        cliente_id="CLI-001",
        tokens=tokens or ("token-a",),
        titulo="Pago de tu seguro paramétrico",
        cuerpo="Recibiste $150.000 por la póliza SOL-1.",
        datos={"siniestro_id": "SIN-1", "tipo": "PAGO_PARAMETRICO"},
        etiqueta="PAGO_PARAMETRICO:2026-12-10",
        total_del_grupo=1,
    )


def error_fcm(estado: int, status: str, codigo: str | None = None, mensaje: str = "error"):
    detalles = (
        [{"@type": "type.googleapis.com/google.firebase.fcm.v1.FcmError", "errorCode": codigo}]
        if codigo
        else []
    )
    cuerpo = {"error": {"code": estado, "status": status, "message": mensaje, "details": detalles}}
    return lambda peticion: httpx.Response(estado, json=cuerpo)


# --- Autenticación -------------------------------------------------------------------------


def test_firma_un_jwt_con_la_cuenta_de_servicio_para_pedir_el_acceso(llaves) -> None:
    enviador, google, _ = crear(llaves)

    enviador.enviar(push())

    (peticion,) = google.peticiones_de_acceso
    campos = parse_qs(peticion.content.decode())
    assert campos["grant_type"] == ["urn:ietf:params:oauth:grant-type:jwt-bearer"]
    reclamos = jwt.decode(
        campos["assertion"][0],
        llaves[1],
        algorithms=["RS256"],
        audience=URL_TOKEN_POR_DEFECTO,
        options={"verify_exp": False, "verify_iat": False},
    )
    assert reclamos["iss"] == CORREO
    assert reclamos["scope"] == ALCANCE
    assert reclamos["exp"] - reclamos["iat"] == 3600


def test_reutiliza_el_token_de_acceso_entre_envios(llaves) -> None:
    enviador, google, _ = crear(llaves)

    enviador.enviar(push("token-a", "token-b"))
    enviador.enviar(push("token-c"))

    assert len(google.peticiones_de_acceso) == 1
    assert len(google.peticiones_de_envio) == 3


def test_renueva_el_token_de_acceso_poco_antes_de_que_venza(llaves) -> None:
    enviador, google, reloj = crear(llaves)
    enviador.enviar(push())

    reloj.avanzar(minutes=50)  # aún le quedan 10 minutos
    enviador.enviar(push())
    assert len(google.peticiones_de_acceso) == 1

    reloj.avanzar(minutes=6)  # ya está dentro del margen de 5 minutos
    enviador.enviar(push())
    assert len(google.peticiones_de_acceso) == 2
    assert google.peticiones_de_envio[-1].headers["Authorization"] == "Bearer acceso-2"


def test_si_google_rechaza_el_acceso_ningun_token_se_envia_y_no_se_filtra_la_llave(
    llaves, caplog
) -> None:
    google = Google(acceso=lambda peticion: httpx.Response(400, json={"error": "invalid_grant"}))
    enviador, google, _ = crear(llaves, google)

    with caplog.at_level(logging.ERROR):
        resultado = enviador.enviar(push("token-a", "token-b"))

    assert resultado.fallidos == ("token-a", "token-b")
    assert resultado.enviados == () and google.peticiones_de_envio == []
    assert "No se pudo obtener el token de acceso" in caplog.text
    assert "PRIVATE KEY" not in caplog.text and llaves[0] not in caplog.text


def test_una_respuesta_de_acceso_sin_token_tambien_falla(llaves) -> None:
    google = Google(acceso=lambda peticion: httpx.Response(200, json={"otra_cosa": 1}))
    enviador, _, _ = crear(llaves, google)

    assert enviador.enviar(push()).fallidos == ("token-a",)


# --- Mensaje -------------------------------------------------------------------------------


def test_envia_el_mensaje_con_el_formato_de_la_api_v1(llaves) -> None:
    enviador, google, _ = crear(llaves)

    enviador.enviar(push("token-a"))

    (peticion,) = google.peticiones_de_envio
    assert str(peticion.url) == "https://fcm.googleapis.com/v1/projects/solventa-test/messages:send"
    assert peticion.headers["Authorization"] == "Bearer acceso-1"
    assert json.loads(peticion.content) == {
        "message": {
            "token": "token-a",
            "notification": {
                "title": "Pago de tu seguro paramétrico",
                "body": "Recibiste $150.000 por la póliza SOL-1.",
            },
            "data": {"siniestro_id": "SIN-1", "tipo": "PAGO_PARAMETRICO"},
            "android": {
                "priority": "HIGH",
                "notification": {
                    "channel_id": CANAL_ANDROID,
                    "tag": "PAGO_PARAMETRICO:2026-12-10",
                    "visibility": "PRIVATE",
                },
            },
        }
    }


def test_manda_una_peticion_por_token_y_los_informa_como_enviados(llaves) -> None:
    enviador, google, _ = crear(llaves)

    resultado = enviador.enviar(push("token-a", "token-b"))

    assert resultado.enviados == ("token-a", "token-b")
    assert resultado.tokens_invalidos == () and resultado.fallidos == ()
    tokens = [json.loads(p.content)["message"]["token"] for p in google.peticiones_de_envio]
    assert tokens == ["token-a", "token-b"]


# --- Clasificación de errores --------------------------------------------------------------


@pytest.mark.parametrize(
    ("respuesta", "esperado"),
    [
        (error_fcm(404, "NOT_FOUND", "UNREGISTERED"), "tokens_invalidos"),
        (error_fcm(403, "PERMISSION_DENIED", "SENDER_ID_MISMATCH"), "tokens_invalidos"),
        (
            error_fcm(
                400,
                "INVALID_ARGUMENT",
                mensaje="The registration token is not a valid FCM registration token",
            ),
            "tokens_invalidos",
        ),
        (error_fcm(400, "INVALID_ARGUMENT", mensaje="Invalid JSON payload"), "fallidos"),
        (error_fcm(429, "RESOURCE_EXHAUSTED", "QUOTA_EXCEEDED"), "fallidos"),
        (error_fcm(503, "UNAVAILABLE", "UNAVAILABLE"), "fallidos"),
        (lambda peticion: httpx.Response(500, text="no es json"), "fallidos"),
        (lambda peticion: httpx.Response(500, json=["raro"]), "fallidos"),
        (lambda peticion: httpx.Response(200, json={"name": "ok"}), "enviados"),
    ],
)
def test_clasifica_cada_respuesta_de_fcm(llaves, respuesta, esperado) -> None:
    enviador, _, _ = crear(llaves, Google(envio=respuesta))

    resultado = enviador.enviar(push("token-a"))

    assert getattr(resultado, esperado) == ("token-a",)


def test_un_error_de_red_deja_el_token_como_fallido(llaves) -> None:
    def sin_red(peticion):
        raise httpx.ConnectError("sin conexión")

    enviador, _, _ = crear(llaves, Google(envio=sin_red))

    resultado = enviador.enviar(push("token-a"))

    assert resultado.fallidos == ("token-a",) and resultado.tokens_invalidos == ()


def test_un_token_malo_no_impide_enviar_a_los_demas(llaves) -> None:
    def segun_token(peticion):
        token = json.loads(peticion.content)["message"]["token"]
        if token == "token-viejo":
            return error_fcm(404, "NOT_FOUND", "UNREGISTERED")(peticion)
        return httpx.Response(200, json={"name": "ok"})

    enviador, _, _ = crear(llaves, Google(envio=segun_token))

    resultado = enviador.enviar(push("token-a", "token-viejo", "token-b"))

    assert resultado.enviados == ("token-a", "token-b")
    assert resultado.tokens_invalidos == ("token-viejo",)


def test_ante_un_401_renueva_el_acceso_y_reintenta_una_vez(llaves) -> None:
    respuestas = iter([httpx.Response(401, json={}), httpx.Response(200, json={"name": "ok"})])
    enviador, google, _ = crear(llaves, Google(envio=lambda peticion: next(respuestas)))

    resultado = enviador.enviar(push("token-a"))

    assert resultado.enviados == ("token-a",)
    assert len(google.peticiones_de_acceso) == 2
    assert google.peticiones_de_envio[-1].headers["Authorization"] == "Bearer acceso-2"


def test_si_el_401_se_repite_el_token_queda_como_fallido_sin_darlo_de_baja(llaves) -> None:
    enviador, google, _ = crear(llaves, Google(envio=lambda peticion: httpx.Response(401, json={})))

    resultado = enviador.enviar(push("token-a"))

    assert resultado.fallidos == ("token-a",) and resultado.tokens_invalidos == ()
    assert len(google.peticiones_de_envio) == 2  # un reintento, no más


# --- Credenciales --------------------------------------------------------------------------


def contenido(**cambios) -> str:
    datos = {"project_id": "solventa-test", "client_email": CORREO, "private_key": "llave"}
    datos.update(cambios)
    return json.dumps({k: v for k, v in datos.items() if v is not None})


def test_carga_las_credenciales_del_contenido_json() -> None:
    credenciales = cargar_credenciales(contenido=contenido(token_uri="https://token.local/t"))

    assert credenciales.project_id == "solventa-test"
    assert credenciales.client_email == CORREO
    assert credenciales.token_uri == "https://token.local/t"


def test_sin_token_uri_usa_el_de_google() -> None:
    assert cargar_credenciales(contenido=contenido()).token_uri == URL_TOKEN_POR_DEFECTO


def test_carga_las_credenciales_de_un_archivo(tmp_path) -> None:
    archivo = tmp_path / "cuenta.json"
    archivo.write_text(contenido(), encoding="utf-8")

    assert cargar_credenciales(ruta=str(archivo)).project_id == "solventa-test"


def test_el_contenido_tiene_prioridad_sobre_la_ruta(tmp_path) -> None:
    archivo = tmp_path / "cuenta.json"
    archivo.write_text(contenido(project_id="del-archivo"), encoding="utf-8")

    credenciales = cargar_credenciales(
        ruta=str(archivo), contenido=contenido(project_id="del-json")
    )

    assert credenciales.project_id == "del-json"


@pytest.mark.parametrize(
    ("argumentos", "mensaje"),
    [
        ({}, "Falta la credencial"),
        ({"contenido": "{no es json"}, "no es un JSON válido"),
        ({"contenido": "[1, 2]"}, "formato esperado"),
        ({"contenido": contenido(private_key=None)}, "private_key"),
        ({"contenido": contenido(project_id=None, client_email=None)}, "project_id, client_email"),
        ({"ruta": "C:/no/existe/cuenta.json"}, "No se pudo leer el archivo"),
    ],
)
def test_credenciales_invalidas_se_rechazan_con_un_mensaje_claro(argumentos, mensaje) -> None:
    with pytest.raises(ConfiguracionPushInvalida, match=mensaje):
        cargar_credenciales(**argumentos)


def test_el_repr_de_las_credenciales_no_muestra_la_llave_privada() -> None:
    credenciales = cargar_credenciales(contenido=contenido(private_key="SECRETO-DE-LA-LLAVE"))

    assert "SECRETO-DE-LA-LLAVE" not in repr(credenciales)
    assert "solventa-test" in repr(credenciales)
