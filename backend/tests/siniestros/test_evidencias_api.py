"""API de evidencias del siniestro (HU04 / EC10)."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.evidencias_siniestro import obtener_servicio
from app.api.seguridad import get_current_user
from app.identidad.modelos import Rol
from app.main import app
from app.siniestros.evidencias import LIMITE_FOTO_BYTES
from app.siniestros.modelos import EstadoSiniestro
from tests.siniestros.fabrica_evidencias import JPEG, MP4, PNG, Entorno, sha, siniestro

RUTA = "/api/v1/siniestros/SIN-1/evidencias"
CLIENTE = SimpleNamespace(id="CLI-001", email="ana@gmail.com", rol=Rol.CLIENTE.value)
OPERADOR = SimpleNamespace(
    id="OPS-1", email="ops@solventa.co", rol=Rol.OPERACIONES_SINIESTROS.value
)
AUDITOR = SimpleNamespace(id="AUD-1", email="aud@solventa.co", rol=Rol.ANALISTA_CUMPLIMIENTO.value)


@pytest.fixture
def entorno():
    datos = Entorno()
    usuario = {"actual": CLIENTE}
    app.dependency_overrides[obtener_servicio] = lambda: datos.servicio
    app.dependency_overrides[get_current_user] = lambda: usuario["actual"]
    yield TestClient(app), datos, usuario
    app.dependency_overrides.clear()


def subir(cliente, contenido=JPEG, tipo="image/jpeg", nombre="foto.jpg", datos=None, headers=None):
    formulario = {
        "capturada_en": "2026-10-21T09:50:00-05:00",
        "latitud": "4.7016",
        "longitud": "-74.1469",
        "precision_metros": "12.5",
    }
    if datos is not None:
        formulario = datos
    return cliente.post(
        RUTA,
        files={"archivo": (nombre, contenido, tipo)},
        data=formulario,
        headers=headers or {},
    )


def test_carga_responde_201_con_metadatos(entorno) -> None:
    cliente, datos, _ = entorno

    r = subir(cliente, headers={"X-Contenido-SHA256": sha(JPEG)})

    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["tipo"] == "FOTO"
    assert cuerpo["huella_sha256"] == sha(JPEG)
    assert cuerpo["geoetiquetada"] is True
    assert cuerpo["latitud"] == 4.7016
    assert cuerpo["capturada_en"].startswith("2026-10-21T14:50:00")
    assert cuerpo["nombre_archivo"] == "foto.jpg"
    # La ubicación interna del archivo no se expone.
    assert "clave_almacenamiento" not in cuerpo
    assert datos.evidencias.contar("SIN-1") == 1


def test_reintento_del_mismo_archivo_responde_200(entorno) -> None:
    cliente, _, _ = entorno
    primera = subir(cliente)
    segunda = subir(cliente)

    assert (primera.status_code, segunda.status_code) == (201, 200)
    assert primera.json()["evidencia_id"] == segunda.json()["evidencia_id"]


def test_sin_ubicacion_ni_fecha_tambien_se_acepta(entorno) -> None:
    cliente, _, _ = entorno
    r = subir(cliente, contenido=MP4, tipo="video/mp4", nombre="video.mp4", datos={})

    assert r.status_code == 201
    assert r.json()["geoetiquetada"] is False
    assert r.json()["tipo"] == "VIDEO"


@pytest.mark.parametrize(
    ("contenido", "tipo", "estado", "codigo"),
    [
        (b"%PDF-1.7", "application/pdf", 415, "TIPO_NO_PERMITIDO"),
        (PNG, "image/jpeg", 422, "CONTENIDO_NO_COINCIDE"),
        (b"", "image/jpeg", 422, "ARCHIVO_VACIO"),
        (JPEG + b"0" * LIMITE_FOTO_BYTES, "image/jpeg", 413, "ARCHIVO_DEMASIADO_GRANDE"),
    ],
)
def test_errores_de_archivo(entorno, contenido, tipo, estado, codigo) -> None:
    cliente, _, _ = entorno
    r = subir(cliente, contenido=contenido, tipo=tipo)
    assert r.status_code == estado
    assert r.json()["detail"]["codigo"] == codigo


def test_huella_distinta_responde_422(entorno) -> None:
    cliente, _, _ = entorno
    r = subir(cliente, headers={"X-Contenido-SHA256": sha(b"otro")})
    assert r.status_code == 422
    assert r.json()["detail"]["codigo"] == "HUELLA_NO_COINCIDE"


def test_huella_con_formato_invalido_responde_422(entorno) -> None:
    cliente, _, _ = entorno
    assert subir(cliente, headers={"X-Contenido-SHA256": "no-es-hex"}).status_code == 422


@pytest.mark.parametrize(
    "datos",
    [
        {"latitud": "4.7"},
        {"latitud": "120", "longitud": "10"},
        {"capturada_en": "ayer"},
        {"capturada_en": "2026-10-21T09:50:00"},  # sin zona horaria
    ],
)
def test_datos_de_captura_invalidos(entorno, datos) -> None:
    cliente, _, _ = entorno
    r = subir(cliente, datos=datos)
    assert r.status_code == 422
    assert r.json()["detail"]["codigo"] == "DATOS_CAPTURA_INVALIDOS"


def test_fecha_de_captura_futura_responde_422(entorno) -> None:
    cliente, _, _ = entorno
    r = subir(cliente, datos={"capturada_en": "2026-10-22T10:00:00-05:00"})
    assert r.status_code == 422
    assert r.json()["detail"]["codigo"] == "FECHA_CAPTURA_INVALIDA"


def test_siniestro_inexistente_o_ajeno_responde_404(entorno) -> None:
    cliente, datos, _ = entorno
    datos.siniestros.guardar(siniestro(siniestro_id="SIN-2", cliente_id="OTRO"))

    r = cliente.post(
        "/api/v1/siniestros/SIN-2/evidencias", files={"archivo": ("f.jpg", JPEG, "image/jpeg")}
    )
    assert r.status_code == 404
    assert r.json()["detail"]["codigo"] == "SINIESTRO_NO_ENCONTRADO"


def test_siniestro_evaluado_responde_409(entorno) -> None:
    cliente, datos, _ = entorno
    datos.siniestros.guardar(siniestro(estado=EstadoSiniestro.APROBADO))
    r = subir(cliente)
    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "SINIESTRO_CERRADO"


def test_operaciones_no_adjunta_pero_si_consulta_y_descarga(entorno) -> None:
    cliente, _, usuario = entorno
    evidencia_id = subir(cliente).json()["evidencia_id"]

    usuario["actual"] = OPERADOR
    assert subir(cliente).status_code == 403
    lista = cliente.get(RUTA)
    assert lista.status_code == 200
    assert lista.headers["cache-control"] == "no-store"
    assert [e["evidencia_id"] for e in lista.json()] == [evidencia_id]

    descarga = cliente.get(f"{RUTA}/{evidencia_id}/contenido")
    assert descarga.status_code == 200
    assert descarga.content == JPEG
    assert descarga.headers["content-type"] == "image/jpeg"
    assert descarga.headers["x-huella-evidencia"] == sha(JPEG)
    assert f'filename="{evidencia_id}.jpg"' in descarga.headers["content-disposition"]


def test_evidencia_alterada_responde_409(entorno) -> None:
    cliente, datos, _ = entorno
    evidencia_id = subir(cliente).json()["evidencia_id"]
    clave = datos.evidencias.obtener(evidencia_id).clave_almacenamiento
    datos.almacen._por_clave[clave] = JPEG + b"editada"

    r = cliente.get(f"{RUTA}/{evidencia_id}/contenido")

    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "EVIDENCIA_ALTERADA"


def test_bitacora_de_auditoria(entorno) -> None:
    cliente, _, usuario = entorno
    subir(cliente)
    cliente.get(RUTA)

    assert cliente.get(f"{RUTA}/auditoria").status_code == 403

    usuario["actual"] = AUDITOR
    r = cliente.get(f"{RUTA}/auditoria")
    assert r.status_code == 200
    assert [a["accion"] for a in r.json()] == ["CARGA", "CONSULTA"]
    assert r.json()[0]["actor_id"] == "CLI-001"


def test_no_hay_forma_de_modificar_ni_borrar(entorno) -> None:
    cliente, _, _ = entorno
    evidencia_id = subir(cliente).json()["evidencia_id"]

    assert cliente.delete(f"{RUTA}/{evidencia_id}/contenido").status_code == 405
    assert cliente.put(f"{RUTA}/{evidencia_id}/contenido", content=PNG).status_code == 405


def test_sin_autenticacion_responde_401() -> None:
    app.dependency_overrides.clear()
    r = TestClient(app).post(RUTA, files={"archivo": ("f.jpg", JPEG, "image/jpeg")})
    assert r.status_code == 401
