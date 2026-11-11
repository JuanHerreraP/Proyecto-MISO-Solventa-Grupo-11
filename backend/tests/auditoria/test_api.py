"""Pruebas del resolutor de pólizas para auditoría (HU25 §8)."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.auditoria import obtener_repositorio
from app.api.seguridad import get_current_user
from app.identidad.modelos import Rol
from app.main import app
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from tests.historial.fabrica import CLIENTE, POLIZA, poliza

NUMERO = "SOLV-VIA-2026-00152"
AUDITOR = SimpleNamespace(
    id="AUD-1", email="auditor@solventa.com", rol=Rol.ANALISTA_CUMPLIMIENTO.value
)


@pytest.fixture
def entorno():
    repo = RepositorioPolizasEnMemoria()
    repo.guardar(poliza())
    app.dependency_overrides[obtener_repositorio] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: AUDITOR
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_resuelve_por_poliza_id_200(entorno) -> None:
    r = entorno.get(f"/api/v1/auditoria/polizas/{POLIZA}")
    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "no-store"
    cuerpo = r.json()
    assert cuerpo["poliza_id"] == POLIZA
    assert cuerpo["numero_poliza"] == NUMERO
    assert cuerpo["cliente_id"] == CLIENTE
    assert cuerpo["nombre_ramo"] == "Seguro de viaje"
    assert cuerpo["estado"] in {"VIGENTE", "VENCIDA", "CANCELADA"}


def test_resuelve_por_numero_de_poliza_200(entorno) -> None:
    r = entorno.get(f"/api/v1/auditoria/polizas/{NUMERO}")
    assert r.status_code == 200
    assert r.json()["poliza_id"] == POLIZA


def test_poliza_inexistente_responde_404(entorno) -> None:
    r = entorno.get("/api/v1/auditoria/polizas/POL-999")
    assert r.status_code == 404
    assert r.json()["detail"]["codigo"] == "POLIZA_NO_ENCONTRADA"


def test_cliente_no_puede_usar_el_resolutor_403(entorno) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=CLIENTE, email="ana@gmail.com", rol=Rol.CLIENTE.value
    )
    r = entorno.get(f"/api/v1/auditoria/polizas/{POLIZA}")
    assert r.status_code == 403
    assert r.json()["detail"]["codigo"] == "ACCESS_DENIED"


def test_sin_autenticacion_responde_401() -> None:
    app.dependency_overrides.clear()
    r = TestClient(app).get(f"/api/v1/auditoria/polizas/{POLIZA}")
    assert r.status_code == 401
