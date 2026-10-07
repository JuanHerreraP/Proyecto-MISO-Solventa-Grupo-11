from fastapi.testclient import TestClient

from app import __version__
from app.main import app

cliente = TestClient(app)


def test_salud_responde_ok():
    respuesta = cliente.get("/salud")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "estado": "ok",
        "servicio": "solventa-backend",
        "version": __version__,
    }


def test_openapi_expone_el_contrato():
    respuesta = cliente.get("/openapi.json")

    assert respuesta.status_code == 200
    assert "/salud" in respuesta.json()["paths"]
