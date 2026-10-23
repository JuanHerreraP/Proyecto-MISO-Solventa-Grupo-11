from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.billetera import obtener_servicio
from app.main import app
from app.polizas.dominio.modelos import EstadoRegistroPoliza
from app.polizas.repositorio import RepositorioEnlacesEnMemoria, RepositorioPolizasEnMemoria
from app.polizas.servicio import ServicioBilletera
from tests.billetera.fabrica import AHORA, poliza

RUTA = "/api/v1/billetera/polizas"
CLIENTE = {"X-Rol": "CLIENTE", "X-Usuario": "CLI-001"}
OTRO_CLIENTE = {"X-Rol": "CLIENTE", "X-Usuario": "CLI-002"}


class Reloj:
    ahora = AHORA

    def __call__(self):
        return self.ahora


@pytest.fixture
def reloj():
    return Reloj()


@pytest.fixture
def polizas():
    return RepositorioPolizasEnMemoria()


@pytest.fixture
def cliente(polizas, reloj, monkeypatch):
    monkeypatch.setenv("SOLVENTA_URL_PUBLICA", "https://api.solventa.co")
    servicio = ServicioBilletera(
        polizas, RepositorioEnlacesEnMemoria(), reloj=reloj, horas_enlace=24
    )
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    yield TestClient(app)
    app.dependency_overrides.pop(obtener_servicio, None)


def test_billetera_vacia(cliente):
    respuesta = cliente.get(RUTA, headers=CLIENTE)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"polizas": [], "total_vigentes": 0, "total_inactivas": 0}
    assert respuesta.headers["Cache-Control"] == "no-store"


def test_el_cliente_ve_sus_polizas_con_vigentes_e_inactivas(cliente, polizas):
    polizas.guardar(poliza())
    polizas.guardar(
        poliza(
            poliza_id="POL-2",
            numero_poliza="SOL-VI-000002",
            estado=EstadoRegistroPoliza.CANCELADA,
        )
    )

    cuerpo = cliente.get(RUTA, headers=CLIENTE).json()

    assert [(p["numero_poliza"], p["estado"], p["activa"]) for p in cuerpo["polizas"]] == [
        ("SOL-VI-000001", "VIGENTE", True),
        ("SOL-VI-000002", "CANCELADA", False),
    ]
    assert cuerpo["polizas"][0]["fecha_inicio"] == "2026-10-01"
    assert cuerpo["polizas"][0]["fecha_fin"] == "2026-12-31"
    assert cuerpo["polizas"][0]["nombre_ramo"] == "Seguro de viaje"


def test_el_cliente_no_ve_polizas_de_otro_titular(cliente, polizas):
    polizas.guardar(poliza())

    assert cliente.get(RUTA, headers=OTRO_CLIENTE).json()["polizas"] == []
    certificado = cliente.get(f"{RUTA}/POL-1/certificado", headers=OTRO_CLIENTE)
    assert certificado.status_code == 404
    assert certificado.json()["detail"]["codigo"] == "POLIZA_NO_ENCONTRADA"
    assert cliente.post(f"{RUTA}/POL-1/enlaces", headers=OTRO_CLIENTE).status_code == 404


def test_otros_roles_no_usan_la_billetera(cliente):
    assert cliente.get(RUTA, headers={"X-Rol": "ASESOR_VENTAS"}).status_code == 403
    assert cliente.get(RUTA, headers={"X-Rol": "SERVICIO_INTERNO"}).status_code == 403


def test_sin_sesion_se_rechaza(cliente):
    assert cliente.get(RUTA).status_code == 401
    assert cliente.get(f"{RUTA}/POL-1/certificado").status_code == 401
    assert cliente.post(f"{RUTA}/POL-1/enlaces").status_code == 401


def test_certificado_con_qr(cliente, polizas):
    polizas.guardar(poliza())

    respuesta = cliente.get(f"{RUTA}/POL-1/certificado", headers=CLIENTE)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["contenido_qr"] == "SOLVENTA|SOL-VI-000001|a1b2c3d4e5f60718"
    assert cuerpo["documento_titular"] == "CC ****5678"
    assert "1012345678" not in respuesta.text


def test_compartir_y_abrir_el_enlace_sin_sesion(cliente, polizas):
    polizas.guardar(poliza())

    creado = cliente.post(f"{RUTA}/POL-1/enlaces", headers=CLIENTE)

    assert creado.status_code == 201
    url = creado.json()["url"]
    assert url.startswith("https://api.solventa.co/api/v1/certificados-compartidos/")
    ruta = url.removeprefix("https://api.solventa.co")

    compartido = cliente.get(ruta)
    assert compartido.status_code == 200
    assert compartido.json()["numero_poliza"] == "SOL-VI-000001"
    assert "prima_total" not in compartido.json()
    assert compartido.headers["Cache-Control"] == "no-store"
    assert compartido.headers["X-Robots-Tag"] == "noindex, nofollow"


def test_el_enlace_abierto_en_un_navegador_se_ve_como_pagina(cliente, polizas):
    polizas.guardar(poliza(titular_nombre="Ana <script>Pérez"))
    url = cliente.post(f"{RUTA}/POL-1/enlaces", headers=CLIENTE).json()["url"]

    pagina = cliente.get(
        url.removeprefix("https://api.solventa.co"), headers={"Accept": "text/html"}
    )

    assert pagina.status_code == 200
    assert pagina.headers["content-type"].startswith("text/html")
    assert "SOL-VI-000001" in pagina.text
    assert "<script>" not in pagina.text
    assert "&lt;script&gt;" in pagina.text


def test_el_enlace_vencido_responde_410(cliente, polizas, reloj):
    polizas.guardar(poliza())
    url = cliente.post(f"{RUTA}/POL-1/enlaces", headers=CLIENTE).json()["url"]
    reloj.ahora = AHORA + timedelta(hours=25)

    respuesta = cliente.get(url.removeprefix("https://api.solventa.co"))

    assert respuesta.status_code == 410
    assert respuesta.json()["detail"]["codigo"] == "ENLACE_VENCIDO"


def test_un_enlace_inventado_responde_404(cliente):
    respuesta = cliente.get("/api/v1/certificados-compartidos/no-existe")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["codigo"] == "ENLACE_NO_ENCONTRADO"


def test_sin_url_publica_configurada_usa_la_del_request(cliente, polizas, monkeypatch):
    monkeypatch.delenv("SOLVENTA_URL_PUBLICA")
    polizas.guardar(poliza())

    url = cliente.post(f"{RUTA}/POL-1/enlaces", headers=CLIENTE).json()["url"]

    assert url.startswith("http://testserver/api/v1/certificados-compartidos/")
